import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

const ThrowError = () => {
  throw new Error('Test error');
};

const SafeComponent = () => <div>Safe content</div>;

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
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
    const onErrorMock = vi.fn();

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
    let shouldThrow = true;
    const ControlledChild = () => {
      if (shouldThrow) throw new Error('Test error');
      return <div>Recovered content</div>;
    };
    const boundary = (child: React.ReactNode) => <ErrorBoundary>{child}</ErrorBoundary>;

    const view = render(boundary(<ControlledChild />));
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    shouldThrow = false;
    view.rerender(boundary(<ControlledChild />));
    fireEvent.click(screen.getByText('Try again'));

    expect(screen.getByText('Recovered content')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
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
