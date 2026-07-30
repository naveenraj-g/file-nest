import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@filenest-fs/core", "@filenest-fs/node", "@filenest-fs/react", "@filenest-fs/nextjs"],
};

export default nextConfig;
