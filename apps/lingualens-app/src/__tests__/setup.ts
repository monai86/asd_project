import "@testing-library/jest-dom/vitest";
import { beforeEach, vi } from "vitest";

import { resetApiRuntimeSettingsCacheForTests } from "@/lib/api";

export const routerPush = vi.fn();
export const routerRefresh = vi.fn();

beforeEach(() => {
  resetApiRuntimeSettingsCacheForTests();
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    refresh: routerRefresh,
  })
}));
