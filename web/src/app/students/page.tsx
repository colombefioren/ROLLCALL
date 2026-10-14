import { Suspense } from "react";
import { StudentsView } from "./StudentsView";

export default function StudentsPage() {
  return (
    <Suspense>
      <StudentsView />
    </Suspense>
  );
}
