/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://driftguard-api:8000/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
