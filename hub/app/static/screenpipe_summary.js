// Course summary from screenpipe, for the teacher to review before sending it to the department head.
//
// MOCK: the real summary is written by the screenpipe pipe on the teacher's computer (work in progress by another teammate).
// Until it is connected, this builds a plausible summary from the coverage the teacher already shared for the course.
// To connect it: keep the signature (course object from GET /api/courses -> summary text) and return the pipe's text instead,
// e.g. read through the local console at https://localhost:4000. Nothing here is sent anywhere; the teacher sends it explicitly.
window.screenpipeSummary = async function screenpipeSummary(course) {
  const covered = course.points.filter((p) => p.covered);
  const missing = course.points.filter((p) => !p.covered);
  const day = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "long" });
  if (!course.lessons.count) {
    return `${course.name} (class ${course.class_id}): no lesson has been recorded and shared for this course yet.`;
  }
  const period = course.lessons.first === course.lessons.last
    ? `on ${day(course.lessons.first)}` : `between ${day(course.lessons.first)} and ${day(course.lessons.last)}`;
  const minutes = covered.reduce((n, p) => n + p.minutes, 0);
  const lines = [
    `${course.name}, class ${course.class_id}: ${course.lessons.count} lesson${course.lessons.count === 1 ? "" : "s"} recorded ${period}.`,
    covered.length
      ? `Taught so far (${Math.round(minutes)} min in total): ${covered.map((p) => `${p.title} (${p.minutes} min)`).join(", ")}.`
      : "No knowledge point of the syllabus has been taught yet.",
    missing.length
      ? `Still to teach: ${missing.map((p) => p.title).join(", ")}.`
      : "Every knowledge point of the syllabus has been taught.",
  ];
  if (covered.length) lines.push(`The class needed the most practice on “${covered[covered.length - 1].title}”; a short review is planned at the start of the next lesson.`);
  if (missing.length) lines.push(`Next: ${missing[0].title}.`);
  await new Promise((r) => setTimeout(r, 400)); // the real pipe answers asynchronously
  return lines.join("\n");
};
