import { initializeTestEnvironment, assertFails, assertSucceeds } from "@firebase/rules-unit-testing";
import { doc, getDoc, setDoc, updateDoc } from "firebase/firestore";

const projectId = "demo-dermcareai";

const tenantDoctor = (uid, org, clinic) => ({
  uid,
  claims: { roles: ["doctor"], organization_id: org, clinic_id: clinic },
});

const main = async () => {
  const testEnv = await initializeTestEnvironment({
    projectId,
    firestore: { rules: "firestore.rules" },
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

    await assertSucceeds(setDoc(doc(doctor.firestore(), "patients/p1"), {
      doctorId: "doctor-1",
      organizationId: "org-1",
      clinicId: "clinic-1",
      name: "Synthetic Test Patient",
    }));

    await assertSucceeds(getDoc(doc(doctor.firestore(), "patients/p1")));
    await assertFails(getDoc(doc(otherTenant.firestore(), "patients/p1")));

    await assertFails(updateDoc(doc(otherTenant.firestore(), "patients/p1"), {
      name: "Cross-tenant write",
    }));

    await testEnv.clearFirestore();
  } finally {
    await testEnv.cleanup();
  }

  console.log("Firestore tenant/RBAC rules: PASS");
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
