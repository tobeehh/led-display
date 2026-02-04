"""Thread-safe primitives for concurrent operations.

Provides building blocks for safe multi-threaded access to shared state.
"""

import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TypeVar, Generic, Callable, Iterator, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


@dataclass
class LockedValue(Generic[T]):
    """Thread-safe value container with read-write lock.

    Provides atomic access to a single value with optional
    update-in-place operations.

    Usage:
        counter = LockedValue(0)
        counter.set(counter.get() + 1)  # Not atomic!
        counter.update(lambda x: x + 1)  # Atomic!

        with counter.locked() as value:
            # Extended operation with lock held
            ...
    """

    _value: T
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def get(self) -> T:
        """Get the current value (thread-safe read)."""
        with self._lock:
            return self._value

    def set(self, value: T) -> None:
        """Set the value (thread-safe write)."""
        with self._lock:
            self._value = value

    def update(self, func: Callable[[T], T]) -> T:
        """Atomically update the value using a function.

        Args:
            func: Function that takes current value and returns new value

        Returns:
            The new value after update
        """
        with self._lock:
            self._value = func(self._value)
            return self._value

    @contextmanager
    def locked(self) -> Iterator[T]:
        """Context manager for extended operations with lock held.

        Yields:
            The current value (modifications won't be saved automatically)
        """
        with self._lock:
            yield self._value


class ThreadSafeDict(Generic[K, V]):
    """Thread-safe dictionary with granular locking.

    Provides dict-like interface with thread safety for all operations.
    For complex operations, use the `locked()` context manager.

    Usage:
        cache = ThreadSafeDict[str, int]()
        cache["key"] = 42
        value = cache.get("key", 0)

        with cache.locked() as d:
            # Complex operations with full lock
            if "key" in d:
                d["key"] += 1
    """

    def __init__(self, initial: dict[K, V] | None = None) -> None:
        self._data: dict[K, V] = dict(initial) if initial else {}
        self._lock = threading.RLock()

    def __getitem__(self, key: K) -> V:
        with self._lock:
            return self._data[key]

    def __setitem__(self, key: K, value: V) -> None:
        with self._lock:
            self._data[key] = value

    def __delitem__(self, key: K) -> None:
        with self._lock:
            del self._data[key]

    def __contains__(self, key: K) -> bool:
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __iter__(self) -> Iterator[K]:
        with self._lock:
            return iter(list(self._data.keys()))

    def get(self, key: K, default: V | None = None) -> V | None:
        """Get value for key, or default if not found."""
        with self._lock:
            return self._data.get(key, default)

    def pop(self, key: K, *args: Any) -> V:
        """Remove and return value for key."""
        with self._lock:
            return self._data.pop(key, *args)

    def keys(self) -> list[K]:
        """Return list of keys (snapshot)."""
        with self._lock:
            return list(self._data.keys())

    def values(self) -> list[V]:
        """Return list of values (snapshot)."""
        with self._lock:
            return list(self._data.values())

    def items(self) -> list[tuple[K, V]]:
        """Return list of (key, value) pairs (snapshot)."""
        with self._lock:
            return list(self._data.items())

    def update(self, other: dict[K, V]) -> None:
        """Update with key-value pairs from another dict."""
        with self._lock:
            self._data.update(other)

    def setdefault(self, key: K, default: V) -> V:
        """Set key to default if not present, return value."""
        with self._lock:
            return self._data.setdefault(key, default)

    def clear(self) -> None:
        """Remove all items."""
        with self._lock:
            self._data.clear()

    def copy(self) -> dict[K, V]:
        """Return a shallow copy of the dictionary."""
        with self._lock:
            return dict(self._data)

    @contextmanager
    def locked(self) -> Iterator[dict[K, V]]:
        """Context manager for complex operations with full lock.

        Yields:
            The underlying dict (direct access while locked)
        """
        with self._lock:
            yield self._data


class StoppableThread(threading.Thread):
    """Thread with clean stop mechanism using Event.

    Provides a standard pattern for daemon threads that need
    to be stopped gracefully.

    Usage:
        def worker(thread: StoppableThread):
            while not thread.should_stop():
                # Do work
                thread.wait(1.0)  # Sleep with stop check

        thread = StoppableThread(target=worker)
        thread.start()
        # Later:
        thread.stop()  # Signals stop and waits
    """

    def __init__(
        self,
        target: Callable[..., Any] | None = None,
        name: str | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        daemon: bool = True,
    ) -> None:
        # If target takes thread as first arg, inject self
        if target is not None:
            original_target = target

            def wrapped_target(*a: Any, **kw: Any) -> Any:
                return original_target(self, *a, **kw)

            super().__init__(target=wrapped_target, name=name, args=args, kwargs=kwargs or {})
        else:
            super().__init__(name=name)

        self.daemon = daemon
        self._stop_event = threading.Event()

    def stop(self, timeout: float = 5.0) -> bool:
        """Request stop and wait for thread to finish.

        Args:
            timeout: Maximum time to wait for thread to finish

        Returns:
            True if thread stopped, False if still running
        """
        logger.debug("Stopping thread: %s", self.name)
        self._stop_event.set()
        self.join(timeout=timeout)
        stopped = not self.is_alive()
        if not stopped:
            logger.warning("Thread %s did not stop within timeout", self.name)
        return stopped

    def should_stop(self) -> bool:
        """Check if stop was requested.

        Returns:
            True if stop() was called
        """
        return self._stop_event.is_set()

    def wait(self, timeout: float) -> bool:
        """Wait with stop check.

        More efficient than time.sleep() as it can be interrupted
        by stop().

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if stop was requested, False if timeout elapsed
        """
        return self._stop_event.wait(timeout)


class AtomicCounter:
    """Thread-safe counter with atomic increment/decrement.

    Usage:
        counter = AtomicCounter()
        counter.increment()
        counter.decrement()
        value = counter.value
    """

    def __init__(self, initial: int = 0) -> None:
        self._value = initial
        self._lock = threading.Lock()

    @property
    def value(self) -> int:
        """Get current counter value."""
        with self._lock:
            return self._value

    def increment(self, delta: int = 1) -> int:
        """Atomically increment counter.

        Returns:
            New value after increment
        """
        with self._lock:
            self._value += delta
            return self._value

    def decrement(self, delta: int = 1) -> int:
        """Atomically decrement counter.

        Returns:
            New value after decrement
        """
        with self._lock:
            self._value -= delta
            return self._value

    def reset(self, value: int = 0) -> int:
        """Reset counter to value.

        Returns:
            Previous value before reset
        """
        with self._lock:
            previous = self._value
            self._value = value
            return previous
