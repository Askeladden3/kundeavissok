import paramiko
import os


def addToWebsite(UKE):
    hostname = "login.stud.ntnu.no"
    port = 22
    username = "askhf"
    password = os.environ['PASSWORD']
    local_file = f"temp_output/databaser/kundeavis_{UKE}_test.db"
    remote_path = f"/web/folk/{username}/{local_file}"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password)

    sftp = ssh.open_sftp()
    sftp.put(local_file, remote_path)  # upload file
    sftp.close()
    ssh.close()