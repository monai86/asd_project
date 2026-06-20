"use client";

import Link from "next/link";
import { useState } from "react";
import { ShieldCheck } from "lucide-react";

type MockRole = "therapist" | "admin";

const roleDestinations: Record<MockRole, string> = {
  therapist: "/today?role=therapist",
  admin: "/settings?scope=admin&role=admin"
};

export function MockLoginFormClient() {
  const [role, setRole] = useState<MockRole>("therapist");
  const destination = roleDestinations[role];

  return (
    <form className="clinical-card self-start rounded-md p-5" aria-label="Mock login form">
      <div className="mb-5 flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-md bg-clinical text-white">
          <ShieldCheck size={20} aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-semibold">Mock login</h2>
          <p className="text-xs text-slate-600">Therapist and admin roles are available for demo.</p>
        </div>
      </div>
      <label className="mb-4 block text-sm font-medium">
        Email
        <input className="mt-1 w-full rounded-md border border-line bg-field px-3 py-2" defaultValue="therapist@example.test" type="email" />
      </label>
      <label className="mb-3 block text-sm font-medium">
        Role
        <select
          className="mt-1 w-full rounded-md border border-line bg-field px-3 py-2"
          value={role}
          onChange={(event) => setRole(event.target.value as MockRole)}
        >
          <option value="therapist">Therapist</option>
          <option value="admin">Admin</option>
        </select>
      </label>
      <p className="mb-4 text-xs text-slate-600" aria-live="polite">
        {role === "admin" ? "Admin opens role-scoped runtime controls." : "Therapist opens Today / Work Queue."}
      </p>
      <Link href={destination} className="inline-flex w-full justify-center rounded-md bg-clinical px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-clinical">
        Enter workspace
      </Link>
    </form>
  );
}
