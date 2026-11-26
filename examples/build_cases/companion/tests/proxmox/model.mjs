// Offline acceptance oracle for a permission-filtered Proxmox guest-card design.
export function guestCard({transport, httpStatus, ageSeconds, body}) {
  if (transport !== "trusted") return {state: "transport unavailable"};
  if (httpStatus === 401 || httpStatus === 403) return {state: "access unavailable"};
  if (httpStatus !== 200) return {state: "service unavailable"};
  if (!Number.isFinite(ageSeconds) || ageSeconds < 0 || ageSeconds > 60) return {state: "stale"};
  if (!Array.isArray(body?.data)) return {state: "invalid response"};
  const seen = new Set();
  const totals = {running: 0, stopped: 0, unknown: 0};
  for (const row of body.data) {
    if (typeof row?.type !== "string") return {state: "invalid response"};
    if (row.type !== "qemu" && row.type !== "lxc") continue;
    if (!Number.isSafeInteger(row.vmid) || row.vmid < 1 || seen.has(row.vmid)) {
      return {state: "invalid response"};
    }
    seen.add(row.vmid);
    if (row.status === "running" || row.status === "stopped") totals[row.status]++;
    else totals.unknown++;
  }
  if (!seen.size) return {state: "no visible guests"};
  return {state: "visible guests", ...totals};
}
