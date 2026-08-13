const mutationMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

const persistenceRouteTemplates: Array<{
  methods: ReadonlySet<string>;
  pattern: RegExp;
  route: string;
}> = [
  {
    methods: new Set(["POST"]),
    pattern: /^\/api\/v1\/cases\/[^/]+\/sessions$/,
    route: "/api/v1/cases/:case_id/sessions",
  },
  {
    methods: new Set(["POST"]),
    pattern: /^\/api\/v1\/sessions\/[^/]+\/transcripts\/manual$/,
    route: "/api/v1/sessions/:session_id/transcripts/manual",
  },
  {
    methods: new Set(["POST"]),
    pattern: /^\/api\/v1\/sessions\/[^/]+\/transcripts\/upload-cha$/,
    route: "/api/v1/sessions/:session_id/transcripts/upload-cha",
  },
  {
    methods: new Set(["PATCH"]),
    pattern: /^\/api\/v1\/transcripts\/[^/]+$/,
    route: "/api/v1/transcripts/:transcript_id",
  },
];

export type MutationResponseBreadcrumb = {
  method: string;
  route: string;
  status: number;
};

export function safeMutationResponseBreadcrumb(
  method: string,
  rawUrl: string,
  status: number,
): MutationResponseBreadcrumb | null {
  const normalizedMethod = method.toUpperCase();
  if (!mutationMethods.has(normalizedMethod)) return null;

  let pathname: string;
  try {
    pathname = new URL(rawUrl).pathname;
  } catch {
    return null;
  }

  const template = persistenceRouteTemplates.find(({ methods, pattern }) => (
    methods.has(normalizedMethod) && pattern.test(pathname)
  ));
  if (!template) return null;

  return { method: normalizedMethod, route: template.route, status };
}
