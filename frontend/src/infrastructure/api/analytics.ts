const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1";

export const analyticsApi = {
  getPickEfficiency: async () => {
    const response = await fetch(`${API_URL}/analytics/efficiency`);
    if (!response.ok) {
      throw new Error("Failed to fetch analytics data");
    }
    return response.json();
  },
};
