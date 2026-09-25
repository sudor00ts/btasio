# btasio Flutter — host + receiver

Un binario. El host parte L/R/M/S por UDP. El receiver reproduce un canal
por el Bluetooth que eligió iOS/Android en Ajustes.

```bash
cd app
flutter create . --org ar.tullio --project-name btasio --platforms=android,ios
flutter pub get
flutter run
```

`flutter create .` no pisa lib/ ni pubspec.yaml.

Permisos Android: INTERNET, ACCESS_NETWORK_STATE, CHANGE_WIFI_MULTICAST_STATE.
iOS Info.plist: NSLocalNetworkUsageDescription + UIBackgroundModes audio.

Prueba: host tono 440/660, receiver rol R → 660 Hz en el parlante BT del sistema.
