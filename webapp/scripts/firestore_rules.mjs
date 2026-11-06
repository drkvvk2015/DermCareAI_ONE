import { initializeTestEnvironment, assertFails, assertSucceeds } from "@firebase/rules-unit-testing";
import { doc, getDoc, setDoc, updateDoc } from "firebase/firestore";
import { readFileSync } from "node:fs";
import { URL, fileURLToPath } from "node:url";

const testEnv = await initializeTestEnvironment({
  projectId: "demo-dermcareai",
  firestore: {
    rules: readFileSync(
      fileURLToPath(new URL("../../firestore.rules", import.meta.url)),
      "utf8",
    ),
  },
});

try {
  await testEnv.withSecurityRulesDisabled(async (context) => {
    await setDoc(doc(context.firestore(), "doctors/doctor-1"), {
      status: "active",
      organizationId: "org-1",
      clinicId: "clinic-1",
    });
  });

  const doctor = testEnv.authenticatedContext(
    "doctor-1",
    { roles: ["doctor"], organization_id: "org-1", clinic_id: "clinic-1" },
  );
  const otherTenant = testEnv.authenticatedContext(
    "doctor-2",
    { roles: ["doctor"], organization_id: "org-2", clinic_id: "clinic-2" },
  );

  await assertFails(getDoc(doc(testEnv.unauthenticatedContext().firestore(), "patients/p1")));

  const admin = testEnv.authenticatedContext(
    "admin-1",
    { roles: ["admin"], organization_id: "org-1", clinic_id: "clinic-1" },
  );

  // Patient creation is restricted to the authenticated server API. Direct
  // Firestore writes must be denied for both tenant doctors and administrators.
  const patient = {
    doctorId: "doctor-1",
    organizationId: "org-1",
    clinicId: "clinic-1",
    name: "Synthetic Test Patient",
  };
  await assertFails(setDoc(doc(doctor.firestore(), "patients/direct-doctor"), patient));
  await assertFails(setDoc(doc(admin.firestore(), "patients/direct-admin"), patient));

  // Seed a synthetic record through the privileged server-side path, then verify
  // tenant-scoped reads remain available to authorized clinicians.
  await testEnv.withSecurityRulesDisabled(async (context) => {
    await setDoc(doc(context.firestore(), "patients/p1"), patient);
  });

  await assertSucceeds(getDoc(doc(doctor.firestore(), "patients/p1")));
  await assertFails(getDoc(doc(otherTenant.firestore(), "patients/p1")));
  await assertFails(updateDoc(doc(otherTenant.firestore(), "patients/p1"), { name: "Cross-tenant write" }));

  await testEnv.clearFirestore();
} finally {
  await testEnv.cleanup();
}
