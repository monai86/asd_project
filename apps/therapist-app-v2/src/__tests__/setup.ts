import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

export const routerPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    prefetch: vi.fn()
  })
}));
