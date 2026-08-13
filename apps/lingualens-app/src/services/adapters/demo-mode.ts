type DemoEnvironment = Readonly<Record<string, string | undefined>>;

export function isDemoEnabled(env: DemoEnvironment = process.env): boolean {
  return env.NEXT_PUBLIC_DEMO_MODE === "true";
}
