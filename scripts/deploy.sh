#!/usr/bin/env bash
# 部署内容站到生产服务器(静态文件覆盖,原子切换;Caddy 配置不动)。
# 前提:本机对 root@47.93.39.204 有 key 认证;DNS 指向后站点即对外。
set -euo pipefail

HOST="root@47.93.39.204"
SITE_DIR="/opt/sma_geo_site"
cd "$(dirname "$0")/.."

npm run build
npm test

STAMP=$(date +%Y%m%d-%H%M%S)
tar czf /tmp/sma-geo-site.tar.gz -C dist .
scp -q /tmp/sma-geo-site.tar.gz "$HOST:/tmp/"
ssh -o BatchMode=yes "$HOST" "
  set -e
  mkdir -p $SITE_DIR/releases/$STAMP
  tar xzf /tmp/sma-geo-site.tar.gz -C $SITE_DIR/releases/$STAMP
  ln -sfn $SITE_DIR/releases/$STAMP $SITE_DIR/current.new
  mv -Tf $SITE_DIR/current.new $SITE_DIR/current
  ls -dt $SITE_DIR/releases/* | tail -n +6 | xargs -r rm -rf
"
echo "deployed release $STAMP -> $SITE_DIR/current (服务器侧部署完成)"
echo "IndexNow 推送自带 DNS 前置门(r6 R1): npm run indexnow —— DNS 未指向目标服务器时自动取消"
