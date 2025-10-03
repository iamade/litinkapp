import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

// Component that throws an error for testing
const ThrowError = () => {
  throw new Error('Test error');
};

// Component that doesn't throw an error
const SafeComponent = () => <div>Safe content</div>;

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress console.error for expected error throws
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <SafeComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Safe content')).toBeInTheDocument();
  });

  it('renders fallback UI when child throws error', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Try again')).toBeInTheDocument();
    expect(screen.getByText('Reload page')).toBeInTheDocument();
  });

  it('shows error message in development mode', () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';

    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Test error')).toBeInTheDocument();

    process.env.NODE_ENV = originalEnv;
  });

  it('calls onError callback when error occurs', () => {
    const onErrorMock = jest.fn();

    render(
      <ErrorBoundary onError={onErrorMock}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(onErrorMock).toHaveBeenCalledWith(
      expect.any(Error),
      expect.any(Object)
    );
  });

  it('resets error state when Try Again button is clicked', () => {
    const SafeAfterReset = () => {
      const [shouldThrow, setShouldThrow] = React.useState(true);

      React.useEffect(() => {
        if (!shouldThrow) {
          // This will be called after reset, so we don't throw
        }
      }, [shouldThrow]);

      if (shouldThrow) {
        throw new Error('Test error');
      }

      return (
        <div>
          <button onClick={() => setShouldThrow(true)}>Throw again</button>
          <div>Recovered content</div>
        </div>
      );
    };

    render(
      <ErrorBoundary>
        <SafeAfterReset />
      </ErrorBoundary>
    );

    // Should show error UI initially
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Click try again
    fireEvent.click(screen.getByText('Try again'));

    // Should show recovered content
    expect(screen.getByText('Recovered content')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    const customFallback = <div>Custom fallback message</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom fallback message')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });
});