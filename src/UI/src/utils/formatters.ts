export function formatBmsDate(dateStr: string): string {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  const y = dateStr.substring(0, 4);
  const m = dateStr.substring(4, 6);
  const d = dateStr.substring(6, 8);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const mIdx = parseInt(m, 10) - 1;
  const mName = months[mIdx] || m;
  return `${parseInt(d, 10)} ${mName} ${y}`;
}

export function formatTimestamp(ts: string | number | null): string {
  if (!ts) return "Never";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return String(ts);
    
    const formatter = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
    const parts = formatter.formatToParts(d);
    const map: Record<string, string> = {};
    parts.forEach(p => { if (p.type !== 'literal') map[p.type] = p.value; });
    return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}:${map.second} IST`;
  } catch (e) {
    return String(ts);
  }
}

export function formatInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const hours = Math.floor(seconds / 3600);
  const remainingAfterHours = seconds % 3600;
  const mins = Math.floor(remainingAfterHours / 60);
  const secs = remainingAfterHours % 60;

  if (hours > 0) {
    if (mins === 0 && secs === 0) return `${hours}h`;
    if (secs === 0) return `${hours}h ${mins}m`;
    return `${hours}h ${mins}m ${secs}s`;
  }

  if (secs === 0) return `${mins}m`;
  return `${mins}m ${secs}s`;
}
