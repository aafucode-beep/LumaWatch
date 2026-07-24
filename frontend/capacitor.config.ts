import type { CapacitorConfig } from '@capacitor/cli'

// Capacitor 打包配置：把前端构建产物包装为安卓 APK。
//
// 打包步骤（在 frontend 目录）：
//   1. 用服务器域名构建前端： VITE_API_BASE=https://intel.example.com npm run build
//   2. 首次初始化安卓平台：    npx cap add android
//   3. 同步产物：              npm run cap:sync
//   4. 打开 Android Studio：   npm run cap:open   （或用 gradlew 直接出包）
//
// 注意：APK 与网站不同源，必须通过 VITE_API_BASE 指向后端 HTTPS 域名。
const config: CapacitorConfig = {
  appId: 'com.lighting.intel',
  appName: '照明情报',
  webDir: 'dist',
  server: {
    // 允许通过 https 访问后端（默认使用打包进 APK 的静态资源）
    androidScheme: 'https',
  },
}

export default config
