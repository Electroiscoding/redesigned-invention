/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@paraearth/shared-types", "@paraearth/ui-config", "@paraearth/planet-gen"],
  webpack: (config) => {
    config.module.rules.push({
      test: /\.wgsl$/i,
      use: 'raw-loader',
    });
    return config;
  },
};

export default nextConfig;