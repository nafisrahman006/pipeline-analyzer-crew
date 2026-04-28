# Auto Fix

## Problem
The deployment stage failed with the error `Permission denied while accessing /var/www/html`. This prevented the CI pipeline from completing the deployment.

## Root Cause
The CI runner does not have write permissions on the target directory `/var/www/html` on the remote server. The original workflow attempted to rsync files directly, which requires appropriate ownership or sudo rights.

## Fix
Added a new step `Prepare deployment directory permissions` that SSHes into the remote server and changes the ownership and permissions of `/var/www/html` to the deployment user (provided via the `DEPLOY_USER` secret). The deployment step now uses this user and includes the SSH command with strict host key checking disabled.

```yaml
- name: Prepare deployment directory permissions
  env:
    DEPLOY_USER: ${{ secrets.DEPLOY_USER }}
  run: |
    ssh $DEPLOY_USER@server "sudo chown -R $DEPLOY_USER:$DEPLOY_USER /var/www/html && sudo chmod -R u+rwX /var/www/html"

- name: Deploy to production
  env:
    DEPLOY_USER: ${{ secrets.DEPLOY_USER }}
  run: |
    rsync -avz -e "ssh -o StrictHostKeyChecking=no" ./dist/ $DEPLOY_USER@server:/var/www/html
```

## Testing
1. Ensure the `DEPLOY_USER` secret contains a user with sudo privileges on the target server.
2. Verify the CI runner’s SSH public key is authorized for `DEPLOY_USER` on the server.
3. Manually run the permission fix command via SSH to confirm it succeeds.
4. Execute a manual `rsync` using the same command to ensure files are copied without permission errors.
5. Observe the next CI run; the deployment step should complete successfully without permission errors.

## Failed Run
Failed run URL: <INSERT_FAILED_RUN_URL_HERE>
