from __future__ import annotations

import abc
from typing import Sequence, Type

import dm_env.specs
import gym.spaces
import gymnasium.spaces
import jax.numpy as jnp
from chex import Array, Shape
import jax
from jax.random import KeyArray


class Space(abc.ABC):
    @abc.abstractproperty
    def shape(self) -> Shape:
        raise NotImplementedError()

    @abc.abstractproperty
    def dtype(self) -> Type:
        raise NotImplementedError()

    @abc.abstractmethod
    def sample(self, key: KeyArray) -> Array:
        raise NotImplementedError()

    @classmethod
    def from_gym(cls, gym_space: gym.spaces.Space) -> Space:
        if isinstance(gym_space, gym.spaces.Discrete):
            return Discrete.from_gym(gym_space)
        elif isinstance(gym_space, gym.spaces.Box):
            return Continuous.from_gym(gym_space)
        else:
            raise NotImplementedError(
                "Cannot convert gym space of type {}".format(type(gym_space))
            )

    @classmethod
    def from_gymnasium(cls, gymnasium_space: gymnasium.spaces.Space) -> Space:
        if isinstance(gymnasium_space, gymnasium.spaces.Discrete):
            return Discrete.from_gymnasium(gymnasium_space)
        elif isinstance(gymnasium_space, gymnasium.spaces.Box):
            return Continuous.from_gymnasium(gymnasium_space)
        else:
            raise NotImplementedError(
                "Cannot convert gymnasium space of type {}".format(
                    type(gymnasium_space)
                )
            )

    @classmethod
    def from_dm_env(cls, dm_space: dm_env.specs.Array) -> Space:
        if isinstance(dm_space, dm_env.specs.DiscreteArray):
            return Discrete.from_dm_env(dm_space)
        elif isinstance(dm_space, dm_env.specs.BoundedArray):
            return Continuous.from_dm_env(dm_space)
        else:
            raise NotImplementedError(
                "Cannot convert dm_env space of type {}".format(type(dm_space))
            )


class Discrete(Space):
    def __init__(self, n_dimensions: int):
        self.n_bins: int = n_dimensions
        self._dtype: Type = jnp.int32

    @property
    def shape(self) -> Shape:
        return (1,)

    @property
    def dtype(self) -> Type:
        return self._dtype

    def __str__(self):
        return "Discrete({})".format(self.n_bins)

    def __repr__(self):
        return self.__str__()

    def sample(self, key: KeyArray) -> Array:
        return jax.random.randint(key, self.shape, 0, self.n_bins + 1)

    @classmethod
    def from_gym(cls, gym_space: gym.spaces.Discrete) -> Discrete:
        return cls(gym_space.n)

    @classmethod
    def from_gymnasium(cls, gymnasium_space: gymnasium.spaces.Discrete) -> Discrete:
        return cls(int(gymnasium_space.n))

    @classmethod
    def from_dm_env(cls, dm_space: dm_env.specs.DiscreteArray) -> Discrete:
        return cls(dm_space.num_values)


class Continuous(Space):
    def __init__(
        self,
        shape: Shape = (1,),
        dtype: Type = jnp.float32,
        minimum: float | Sequence[float] | Array = -1.0,
        maximum: float | Sequence[float] | Array = 1.0,
    ):
        self._shape: Shape = shape
        self._dtype = dtype
        self.min: Array = jnp.broadcast_to(jnp.asarray(minimum), shape=shape)
        self.max: Array = jnp.broadcast_to(jnp.asarray(maximum), shape=shape)

        assert (
            self.min.shape == self.max.shape == shape
        ), "minimum and maximum must have the same length as n_dimensions, got {} and {} for n_dimensions={}".format(
            self.min.shape, self.max.shape, shape
        )

    @property
    def shape(self) -> Shape:
        return self._shape

    @property
    def dtype(self) -> Type:
        return self._dtype

    def __str__(self):
        return "Continuous(shape={}, dtype={})".format(self._shape, self._dtype)

    def __repr__(self):
        return self.__str__()

    def sample(self, key: KeyArray) -> Array:
        if jnp.issubdtype(self.dtype, jnp.integer):
            out = jax.random.randint(
                key, self.shape, self.min, self.max, dtype=self.dtype
            )
            return out
        elif jnp.issubdtype(self.dtype, jnp.floating):
            return jax.random.uniform(
                key, self.shape, minval=self.min, maxval=self.max, dtype=self.dtype
            )
        else:
            raise NotImplementedError(
                "Cannot sample from space of type {}".format(self.dtype)
            )

    @classmethod
    def from_gym(cls, gym_space: gym.spaces.Box) -> Continuous:
        shape = gym_space.shape
        minimum = jnp.asarray(gym_space.low)
        maximum = jnp.asarray(gym_space.high)
        return cls(shape=shape, dtype=gym_space.dtype, minimum=minimum, maximum=maximum)

    @classmethod
    def from_gymnasium(cls, gymnasium_space: gymnasium.spaces.Box) -> Continuous:
        shape = gymnasium_space.shape
        minimum = jnp.asarray(gymnasium_space.low)
        maximum = jnp.asarray(gymnasium_space.high)
        return cls(
            shape=shape, dtype=gymnasium_space.dtype, minimum=minimum, maximum=maximum
        )

    @classmethod
    def from_dm_env(cls, dm_space: dm_env.specs.BoundedArray) -> Continuous:
        shape = dm_space.shape
        minimum = jnp.asarray(dm_space.minimum)
        maximum = jnp.asarray(dm_space.maximum)
        return cls(shape=shape, dtype=dm_space.dtype, minimum=minimum, maximum=maximum)
