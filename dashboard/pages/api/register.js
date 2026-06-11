export default async function handler(req, res) {
  const backendUrl = process.env.DRIFTGUARD_API_URL || 'http://localhost:8000';

  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method Not Allowed' });
  }

  try {
    const response = await fetch(`${backendUrl}/users/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(req.body)
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
    console.error("Proxy error in /api/register:", error);
    return res.status(500).json({ detail: 'Cannot connect to DriftGuard API' });
  }
}
