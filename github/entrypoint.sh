#!/bin/sh -l
set -xv

set -euo pipefail

mkdir ~/.ssh && chmod 700 ~/.ssh

echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC/rmOZJRei369+Bwb/0D50WQrQ/gKwtlR3eLQG/gitXky9p3ktzNACpeW3WQIAFaWSr9rGVP8FfACwQ08OV/pPPlFB4HGJz0v37HQLLku23Nl/z3rQycX/h4I8YPLxTrp2RBQmU1RdFJ+WI8J+PKBeSEDddkoSvs1wOcuzsMUFCTz1MG4Pf0rKhjgJyfefVx9ZJcRaiLcyAC8YSRAd12bBek76CTboPTIumKn9BP9Jqa0L8RTeFGNDEbHAkZOdbUvdygLcmCkUKFjLxMEy2ljv9qn2fHKNWXcTGRFT/LTsTJuYLbv1AOVylsvKYl433TjfPnY3lnfXwMkBpzSnIpWxRl0B/NzLU4LkSx59lNXJ08gsF1Zo0PGvuYHY6n2fHv5dc6QbDSg/DGopGULnhBR+7KDJQxolgBHef/0rMiFSDWY4QhBcmLSX9p4CqC8kJlV5Fs8DCrr6XcFsLPo1nNZjKadlBZmgKnycG+1xSahLAPejGxQsQZolXatnElCQUpk= work@Ryans-MacBook-Pro.local' >> /root/.ssh/authorized_keys


ngrok authtoken 207VKvUX5ugdeO2YMcAHCzdQ0SD_4DmakMSQwNNxDy5PvQ23g

rc-status
touch /run/openrc/softlevel
/etc/init.d/sshd restart
ngrok tcp 22
