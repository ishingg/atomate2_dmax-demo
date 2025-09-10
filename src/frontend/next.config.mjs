/** @type {import('next').NextConfig} */
const nextConfig = {
    rewrites: async () => {
        return [
          {
            source: '/atomate2-api/:path*',
            destination: 'http://127.0.0.1:5000/atomate2-api/:path*',
          },
        ]
      },
};

export default nextConfig;
