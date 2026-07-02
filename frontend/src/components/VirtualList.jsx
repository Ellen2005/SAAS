import React, { useRef, useEffect, useState, useCallback } from 'react';

/**
 * Virtual scrolling component for rendering large lists efficiently
 * Only renders visible items + overscan buffer
 */
export default function VirtualList({
  items = [],
  itemHeight = 50,
  containerHeight = 600,
  overscan = 5,
  renderItem,
  className = '',
  style = {},
}) {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef(null);

  const totalHeight = items.length * itemHeight;
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(items.length, startIndex + visibleCount + overscan * 2);
  const visibleItems = items.slice(startIndex, endIndex);
  const offsetY = startIndex * itemHeight;

  const handleScroll = useCallback((e) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        height: containerHeight,
        overflow: 'auto',
        position: 'relative',
        ...style,
      }}
    >
      <div
        style={{
          height: totalHeight,
          position: 'relative',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: offsetY,
            left: 0,
            right: 0,
          }}
        >
          {visibleItems.map((item, index) => (
            <div
              key={item.id || startIndex + index}
              style={{
                height: itemHeight,
                overflow: 'hidden',
              }}
            >
              {renderItem(item, startIndex + index)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Hook for lazy loading images/components
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useLazyLoad(threshold = 0.1) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [threshold]);

  return { ref, isVisible, isLoaded, setIsLoaded };
}

/**
 * Hook for debouncing values (useful for search inputs)
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Hook for throttling function calls
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useThrottle(callback, delay = 1000) {
  const lastCallRef = useRef(0);
  const timeoutRef = useRef(null);

  return useCallback((...args) => {
    const now = Date.now();
    const timeSinceLastCall = now - lastCallRef.current;

    if (timeSinceLastCall >= delay) {
      lastCallRef.current = now;
      callback(...args);
    } else {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        lastCallRef.current = Date.now();
        callback(...args);
      }, delay - timeSinceLastCall);
    }
  }, [callback, delay]);
}

/**
 * Hook for memoizing expensive calculations
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useMemoized(callback, dependencies) {
  // eslint-disable-next-line react-hooks/use-memo, react-hooks/exhaustive-deps
  const memoizedValue = React.useMemo(callback, dependencies);
  return memoizedValue;
}

/**
 * Hook for lazy loading components
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useLazyComponent(importFn, options = {}) {
  const { suspense: _suspense = true } = options;
  const [component, setComponent] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (component || loading) return;
    
    setLoading(true);
    try {
      const module = await importFn();
      setComponent(() => module.default || module);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [importFn, component, loading]);

  useEffect(() => {
    load();
  }, [load]);

  return { component, error, loading, load };
}