import "@testing-library/jest-dom";

// Mock fetch globally
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, val) => { store[key] = String(val); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock Next.js router
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  useSearchParams: () => ({ get: jest.fn(() => null) }),
  usePathname: () => "/",
}));

// Reset mocks between tests
beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
  // Default fetch: return 404 so fetchWorkerProfile returns null gracefully
  global.fetch.mockResolvedValue({
    ok: false,
    status: 404,
    json: async () => ({}),
  });
});
