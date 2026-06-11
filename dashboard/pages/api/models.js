export default async function handler(req, res) {
  const backendUrl = process.env.DRIFTGUARD_API_URL || 'http://localhost:8000';
  const apiKey = req.headers['x-api-key'] || '';

  if (req.method !== 'GET') {
    return res.status(405).json({ detail: 'Method Not Allowed' });
  }

  try {
    const response = await fetch(`${backendUrl}/models`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      }
    });

    const text = await response.text();
    res.status(response.status);
    try {
      const data = JSON.parse(text);
      return res.json(data);
    } catch (_) {
      return res.send(text);
    }
  } catch (error) {
    console.error("Proxy error in /api/models:", error);
    return res.status(500).json({ detail: 'Cannot connect to DriftGuard API' });
  }
}
