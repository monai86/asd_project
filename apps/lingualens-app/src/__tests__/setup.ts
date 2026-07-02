import "@testing-library/jest-dom/vitest";
import { render, type RenderResult } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import { resetApiRuntimeSettingsCacheForTests } from "@/lib/api";

export const routerPush = vi.fn();
export const routerRefresh = vi.fn();

type AsyncPage<TProps = any> = (props: TProps) => React.ReactNode | Promise<React.ReactNode>;

export async function renderAsyncPage(
  page: AsyncPage,
  props?: unknown,
) {
  const content = await page((props ?? {}) as any);
  return render(content);
}

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
