import type { NextConfig } from "next";

const nextConfig: NextConfig = {
   // Docker (9.5.3): build a self-contained server (.next/standalone) so the image needs no modules folder

    output: "standalone"
};

export default nextConfig;
