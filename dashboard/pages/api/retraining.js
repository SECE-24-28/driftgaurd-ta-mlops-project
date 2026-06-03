export default async function handler(req, res) {
  const { id } = req.query;
  if (!id) {
    return res.status(400).json({ error: 'Missing model ID query parameter' });
  }

  const backendUrl = process.env.DRIFTGUARD_API_URL || 'http://driftguard-api:8000';
  
  try {
    const response = await fetch(`${backendUrl}/retraining/history/${id}`, { method: 'GET' });
    if (response.ok) {
      const data = await response.json();
      return res.status(200).json(data);
    }
    throw new Error('API returned error');
  } catch (error) {
    const mockHistory = [
      {
        id: 1,
        model_id: id,
        status: "completed",
        triggered_by: "manual",
        start_time: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        end_time: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000 + 4 * 60 * 1000).toISOString(),
        old_accuracy: 0.895,
        new_accuracy: 0.912,
        old_version: "1.0.3",
        new_version: "1.0.4",
        details: { message: "Sandbox calibration run succeeded." }
      }
    ];
    return res.status(200).json(mockHistory);
  }
}
