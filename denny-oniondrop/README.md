# OnionDrop for Umbrel

This folder is the Umbrel package for OnionDrop 0.1.0.

Before publishing it, build and push `dennysubke/oniondrop:0.1.0`, retrieve the multiarch digest, and append it to the image reference in `docker-compose.yml`. Upload the logo and three gallery images to the paths already defined in `umbrel-app.yml`.

Port `8397` was not present in the current app table of Denny's Umbrel App Store when this package was created.
