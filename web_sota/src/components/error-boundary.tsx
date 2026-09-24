import { Component, type ReactNode } from "react";

/** Page-level error boundary: one crashing page must never blank the app.
 *
 * Added after a string lat/lon from real GTFS data threw inside Stops and
 * unmounted the entire tree (black screen, sidebar included).
 */
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error("[page-error]", error);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          data-testid="page-error"
          className="rounded-xl border border-red-900/60 bg-red-950/20 p-6 text-sm"
        >
          <p className="font-medium text-red-300">
            This page crashed: {this.state.error.message}
          </p>
          <p className="mt-1 text-slate-400">
            The sidebar still works - switch pages freely. Details are in the
            browser console.
          </p>
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="mt-3 rounded-lg border border-slate-600 px-3 py-1.5 text-slate-200 hover:bg-slate-800"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
