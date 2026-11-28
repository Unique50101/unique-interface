/** Call a Unique Interface app from a same-origin browser or a Node script. */
export class Client {
  constructor(url) { this.url = url.replace(/\/$/, ''); }

  async schema() {
    const response = await fetch(this.url + '/api/schema');
    if (!response.ok) throw new Error('Schema request failed: ' + response.status);
    return response.json();
  }

  async predict(inputs, name = 'predict', options = {}) {
    const response = await fetch(this.url + '/api/' + encodeURIComponent(name), {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({inputs}), signal: options.signal
    });
    if (!response.ok) throw new Error('Prediction failed: ' + response.status);
    return response.json();
  }
}
