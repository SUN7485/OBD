# FleetMobile project commands

## EAS Build (run from `FleetMobile/`)
```bash
eas build --platform android --profile preview
```

## EAS logs
```bash
eas build:logs <BUILD_ID> --platform android
```

## Run locally
```bash
cd FleetMobile
npm start
npm run android
```

## Android signing / profile setup
- Remote credentials are configured with "Build Credentials 7G0O7cPCNZ (default)".
- Preview uses internal distribution.
