import paramiko
import shutil
import os
from jinja2 import Environment, FileSystemLoader

def create_frontend_files(UKE: int, Alle_butikker, nedlastede_butikker):

    finenavn_dict = {'rema-1000':'Rema 1000', 'kiwi': 'Kiwi', 'extra': 'Coop Extra',
                     'bunnpris': 'Bunnpris','meny': 'Meny','coop-prix': 'Coop Prix',
                     'joker': 'Joker','spar': 'Eurospar','coop-mega': 'Coop Mega',
                     'coop-marked': 'Coop Marked','obs': 'Coop Obs'}

    folder_path = "temp_output/bilder/"

    '''
    nedlastede_butikker = set()
    for entry in os.listdir(folder_path):
        butikknavn = entry.split('_')[0]
        nedlastede_butikker.add(butikknavn)
    '''
    utilgjengelige_butikker = set(Alle_butikker).difference(nedlastede_butikker)

    if not utilgjengelige_butikker:
        util_butikkstr = 'Ingen'
    else:
        utilgjengelige_butikker = list(utilgjengelige_butikker)
        util_butikkstr = f'{finenavn_dict[utilgjengelige_butikker[0]]}'
        for butikk in utilgjengelige_butikker[1:]:
            util_butikkstr += ', ' + finenavn_dict[butikk]

    data_html = {
        'index_uke': UKE,
        'utilgjengelige_butikker': util_butikkstr
    }
    
    data_php = {
        'search_uke': UKE
    }


    file_loader = FileSystemLoader('frontend_templates')

    env_html = Environment(loader=file_loader)
    html_template = env_html.get_template('htmltemplate.html')
    output_html = html_template.render(**data_html)

    with open('temp_output/index.html', 'w', encoding='utf-8') as f:
        f.write(output_html)
    

    env_php = Environment(loader=file_loader)
    php_template = env_php.get_template('phptemplate.php.j2')
    output_php = php_template.render(**data_php)

    with open('temp_output/search.php', 'w', encoding='utf-8') as f:
        f.write(output_php)


def updateWebsite(UKE):
    hostname = "login.stud.ntnu.no"
    port = 22
    username = "askhf"
    password = os.environ['PASSWORD']

    local_files = [f"temp_output/databaser/kundeavis_{UKE}.db", "temp_output/index.html", "temp_output/search.php"]
    remote_paths = [f"/web/folk/{username}/databaser/kundeavis_{UKE}.db", f"/web/folk/{username}/index.html", f"/web/folk/{username}/search.php"]
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password)

    sftp = ssh.open_sftp()
    for index in range(len(local_files)):
        sftp.put(local_files[index], remote_paths[index])
    sftp.close()
    ssh.close()

def zip_and_saveFiles(dato):

    current_date, år, uke = dato
    formatting = 'zip'
    archive_name = f'kundeavisfiler_{år}_{uke}'
    full_fileName = archive_name + "." + formatting

    shutil.make_archive(archive_name, formatting, 'temp_output/results_JSON')
    hostname = "login.stud.ntnu.no"
    port = 22
    username = "askhf"
    password = os.environ['PASSWORD']

    local_file = full_fileName
    remote_path = f"/web/folk/{username}/arkiv/{full_fileName}"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password)

    sftp = ssh.open_sftp()
    sftp.put(local_file, remote_path)
    sftp.close()
    ssh.close()

def updateWebsite_testing(UKE):
    hostname = "login.stud.ntnu.no"
    port = 22
    username = "askhf"
    password = os.environ['PASSWORD']

    local_files = [f"temp_output/databaser/kundeavis_{UKE}.db"]
    remote_paths = [f"/web/folk/{username}/databaser/kundeavis_{UKE}_testdatabase.db"]

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password)

    sftp = ssh.open_sftp()
    for index in range(len(local_files)):
        sftp.put(local_files[index], remote_paths[index])
    sftp.close()
    ssh.close()

