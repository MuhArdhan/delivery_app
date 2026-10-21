// API Client for Frappe Delivery App Backend

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

export function getCsrfToken() {
  return window.csrf_token || getCookie('csrf_token') || '';
}

export async function callApi(method, args = {}, httpMethod = 'POST') {
  const headers = {
    'Accept': 'application/json',
    'X-Frappe-CSRF-Token': getCsrfToken(),
  };

  let url = `/api/method/${method}`;
  let options = {
    method: httpMethod,
    headers,
  };

  if (httpMethod === 'GET') {
    const params = new URLSearchParams();
    for (const [key, val] of Object.entries(args)) {
      if (val !== undefined && val !== null) {
        params.append(key, typeof val === 'object' ? JSON.stringify(val) : val);
      }
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  } else {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(args);
  }

  try {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
      let errorMsg = 'Terjadi kesalahan sistem';
      if (data._server_messages) {
        try {
          const msgs = JSON.parse(data._server_messages);
          const parsed = JSON.parse(msgs[0]);
          errorMsg = parsed.message || errorMsg;
        } catch (e) {
          errorMsg = data._server_messages;
        }
      } else if (data.message) {
        errorMsg = typeof data.message === 'string' ? data.message : JSON.stringify(data.message);
      } else if (data.exception) {
        errorMsg = data.exception;
      }
      throw new Error(errorMsg);
    }

    return data.message !== undefined ? data.message : data;
  } catch (err) {
    console.error(`API Call failed [${method}]:`, err);
    throw err;
  }
}

export const DeliveryApi = {
  getSummary: () => callApi('delivery_app.api.get_operations_summary', {}, 'GET'),
  getNotes: (filters) => callApi('delivery_app.api.get_delivery_notes', filters, 'GET'),
  getNoteDetail: (name) => callApi('delivery_app.api.get_delivery_note_detail', { delivery_note: name }, 'GET'),
  dispatchEkspedisi: (payload) => callApi('delivery_app.api.dispatch_ekspedisi', payload, 'POST'),
  createTrip: (payload) => callApi('delivery_app.api.create_delivery_trip', payload, 'POST'),
  submitTrip: (tripName) => callApi('delivery_app.api.submit_delivery_trip', { trip_name: tripName }, 'POST'),
  startTrip: (tripName) => callApi('delivery_app.api.start_trip', { trip_name: tripName }, 'POST'),
  completeTrip: (tripName) => callApi('delivery_app.api.complete_trip', { trip_name: tripName }, 'POST'),
  getTrips: (filters) => callApi('delivery_app.api.get_delivery_trips_list', filters, 'GET'),
  getTripDetail: (tripName) => callApi('delivery_app.api.get_delivery_trip_detail', { trip_name: tripName }, 'GET'),
  getFleetResources: () => callApi('delivery_app.api.get_fleet_resources', {}, 'GET'),
  getPods: (filters) => callApi('delivery_app.api.get_pods_list', filters, 'GET'),
  getSettings: () => callApi('delivery_app.api.get_gateway_settings_api', {}, 'GET'),
  saveSettings: (payload) => callApi('delivery_app.api.save_gateway_settings_api', payload, 'POST'),
  trackWaybill: (dnName) => callApi('delivery_app.api.track_waybill_live', { delivery_note: dnName }, 'POST'),
  estimateRates: (payload) => callApi('delivery_app.api.check_rates_estimate', payload, 'GET'),
  submitPod: (payload) => callApi('delivery_app.api.submit_pod', payload, 'POST'),
  getCustomerLocation: (customer) => callApi('delivery_app.api.get_customer_delivery_location', { customer }, 'GET'),
  setCustomerLocation: (customer, latitude, longitude) => callApi('delivery_app.api.set_customer_delivery_location', { customer, latitude, longitude }, 'POST'),
  getCompanyDispatchLocation: (company) => callApi('delivery_app.api.get_company_dispatch_location', { company }, 'GET'),
  setCompanyDispatchLocation: (company, latitude, longitude) => callApi('delivery_app.api.set_company_dispatch_location', { company, latitude, longitude }, 'POST'),
  markTripDeparted: (tripName) => callApi('delivery_app.api.mark_trip_departed', { trip_name: tripName }, 'POST'),
};
