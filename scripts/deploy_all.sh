#!/bin/bash
set -e

export CLOUDFLARE_ACCOUNT_ID="66ca2679635ad3f328dab2ef6ec24292"
echo "Starting deployment of active static web apps to Cloudflare Account: $CLOUDFLARE_ACCOUNT_ID"

# 1. public-screening
echo "=== Building and Deploying public-screening ==="
cd public-screening
npm run build
npx wrangler pages deploy dist --project-name=asd-public-screening --branch=main
cd ..

# 2. presentation-dashboard
echo "=== Building and Deploying presentation-dashboard ==="
cd presentation-dashboard
npm run build
npx wrangler pages deploy dist --project-name=asd-presentation-dashboard --branch=main
cd ..

echo "=== Static web apps deployed successfully! ==="
