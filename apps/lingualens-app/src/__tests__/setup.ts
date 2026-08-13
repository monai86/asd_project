import "@testing-library/jest-dom/vitest";
import { render, type RenderResult } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import { resetApiRuntimeSettingsCacheForTests } from "@/lib/api";

export const routerPush = vi.fn();
export const routerRefresh = vi.fn();
export const redirectMock = vi.fn((href: string): never => {
  const error = new Error("NEXT_REDIRECT");
  Object.assign(error, { digest: `NEXT_REDIRECT;replace;${href};307;` });
  throw error;
});

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
  redirect: redirectMock,
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    refresh: routerRefresh,
  })
}));
