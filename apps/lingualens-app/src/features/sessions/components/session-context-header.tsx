import { PageHeader } from "@/components/page-header";

export type SessionContextHeaderProps = {
  title: string;
  description: string;
  meta?: string[];
};

export function SessionContextHeader(props: SessionContextHeaderProps) {
  return <PageHeader {...props} />;
}
