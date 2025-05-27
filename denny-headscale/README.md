# Headscale Self-Hosting Guide

## Introduction

This guide provides instructions for setting up and configuring a self-hosted Headscale installation on Umbrel.

## Initial Setup After Installation

After installing Headscale from the Umbrel app store, you need to configure the server's host information:

1.  Open the Files app from the Umbrel dashboard.
2.  Navigate to `apps` → `denny-headscale`.
3.  Locate and download the `exports.sh` file to your computer.
4.  Open the file in a text editor and update the following line with your Umbrel's IP address:

    ```bash
    # Replace with your Umbrel's IP or host name
    export UMBREL_HOST="172.17.0.2" # your's might be different
    ```

5.  Save the file and upload it back to the same location.
6.  Next, navigate into the `config` directory within the `denny-headscale` app folder (`apps` → `denny-headscale` → `config`).
7.  Locate and download the `config.yaml` file to your computer.
8.  Open `config.yaml` in a text editor and find the `server_url` parameter replace `umbrel.local` with your Umbrel's actual IP address. If that's how you access your Umbrel:

    ```yaml
    server_url: http://172.17.0.2:37070
    # OR if you prefer to use the local hostname:
    # server_url: http://umbrel.local:37070
    ```

9.  Save the `config.yaml` file and upload it back to the `config` directory.
10. Restart the Headscale app from the Umbrel dashboard.

This configuration is essential for proper function of Headscale, ensuring both the server's host and the client connection URL are correctly set.

## Generating API Keys and Accessing the Web UI

### Generating an API Key

To generate an API key for Headscale, execute the following command in your terminal:

```bash
sudo docker exec -it denny-headscale_headscale_1 headscale apikeys create
```

**Important:** Store the generated API key securely as you will not be able to retrieve it later. You can generate as many API keys as needed.

### Accessing the Web UI

The Headscale web user interface (UI) can be accessed by navigating to either of the following paths in your web browser, appended to your Umbrel's IP address or hostname and the Headscale port (37070):

* `/web`
* `/admin`

For example:
- If your Umbrel's IP address is 172.17.0.2, you'd access the web UI by going to http://172.17.0.2:37070/web or http://172.17.0.2:37070/admin.

- If you're using umbrel.local to access your Umbrel, you'd go to http://umbrel.local:37070/web or http://umbrel.local:37070/admin.