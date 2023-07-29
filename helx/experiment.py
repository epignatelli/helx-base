from typing import Tuple
import jax
from jax.random import KeyArray
import jax.numpy as jnp
import wandb

from .environment.environment import Environment

from .agents.agent import AgentState
from .mdp import Timestep, StepType
from .agents import Agent
from .logging import Log, host_log_wandb


def run_episode(
    agent: Agent,
    agent_state: AgentState,
    env: Environment,
    eval: bool = False,
    *,
    key: KeyArray,
) -> Timestep:
    key, k1 = jax.random.split(key)
    timestep = env.reset(k1)
    timesteps = [timestep]
    while timestep.step_type == StepType.TRANSITION:
        key, k1, k2 = jax.random.split(key, 3)
        action = agent.sample_action(
            agent_state, timestep.observation, key=k1, eval=eval
        )
        timestep = env.step(k2, timestep, action)
        timesteps.append(timestep)

    # convert list of timesteps into a batched timestep object
    timesteps = jax.tree_util.tree_map(lambda *x: jnp.stack(x), *timesteps)
    return timesteps


def run_n_steps(
    agent: Agent,
    env: Environment,
    agent_state: AgentState,
    env_state: Timestep,
    n_steps: int,
    *,
    key: KeyArray,
    eval: bool = False,
) -> Timestep:
    timesteps = [env_state]
    for _ in range(n_steps):
        key, k1, k2 = jax.random.split(key, num=3)
        action = agent.sample_action(
            agent_state, env_state.observation, key=k1, eval=eval
        )
        env_state = env.step(k2, env_state, action)
        timesteps.append(env_state)

    # convert list of timesteps into a batched timestep object
    timesteps = jax.tree_util.tree_map(lambda *x: jnp.stack(x), *timesteps)
    return timesteps


def run(
    agent: Agent,
    env: Environment,
    max_timesteps: int,
    *,
    key: KeyArray,
) -> Tuple[AgentState, Timestep]:
    # init
    key, k1, k2 = jax.random.split(key, num=3)
    env_state = env.reset(key=k1)
    agent_state = agent.init(key=k2)
    wandb.init(mode="disabled")

    for _ in range(max_timesteps):
        key, k1, k2 = jax.random.split(key, num=3)
        timesteps = run_n_steps(
            agent, env, agent_state, env_state, n_steps=agent.hparams.n_steps, key=key
        )
        agent_state = agent.update(agent_state, timesteps, key=key)

        host_log_wandb(
            agent_state.log
        )  # potentially blocking, this call is on the host, not on the device, despite jitting

    return agent_state, env_state


def jrun(
    agent: Agent,
    env: Environment,
    max_timesteps: int,
    *,
    key: KeyArray,
) -> Tuple[AgentState, Timestep]:
    def body_fun(
        val: Tuple[AgentState, Timestep, KeyArray]
    ) -> Tuple[AgentState, Timestep, KeyArray]:
        agent_state, env_state, key = val
        key, k1, k2 = jax.random.split(key, num=3)
        timesteps = run_n_steps(
            agent, env, agent_state, env_state, n_steps=agent.hparams.n_steps, key=k1
        )
        agent_state = agent.update(agent_state, timesteps, key=k2)
        host_log_wandb(
            agent_state.log
        )  # potentially blocking, this call is on the host, not on the device, despite jitting
        return agent_state, env_state, key

    # init
    key, k1, k2 = jax.random.split(key, num=3)
    env_state = env.reset(key=k1)
    agent_state = agent.init(key=k2)

    agent_state, env_state, _ = jax.lax.while_loop(
        lambda x: x[0].iteration < max_timesteps,
        body_fun,
        (
            agent_state,
            env_state,
            key,
        ),
    )
    return agent_state, env_state
