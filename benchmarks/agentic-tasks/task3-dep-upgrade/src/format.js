import { formatDistance } from "date-fns";

// Wraps date-fns for the app. The project is moving from date-fns v2 to v4
// (the upgrade is the task — see TASK.md). Under v2 this file is correct
// except it must also keep working after `npm i date-fns@4`.
export function postedAt(dateLike) {
  return formatDistance(new Date(dateLike), new Date(), { addSuffix: true });
}