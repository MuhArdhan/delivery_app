// Keep stored ERPNext values compatible; describe tracking, not vehicle ownership.
export function trackingMethodLabel(method) {
  if (method === 'Ekspedisi') return 'Resi Ekspedisi'
  if (!method || method === 'Armada Sendiri') return 'Checkpoint Scanner'
  return method
}
