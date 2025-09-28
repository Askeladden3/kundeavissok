import paramiko
import os
from jinja2 import Environment, FileSystemLoader

def create_frontend_files(UKE: int):

    finenavn_dict = {'rema-1000':'Rema 1000', 'kiwi': 'Kiwi', 'extra': 'Coop Extra',
                     'bunnpris': 'Bunnpris','meny': 'Meny','coop-prix': 'Coop Prix',
                     'joker': 'Joker','spar': 'Eurospar','coop-mega': 'Coop Mega',
                     'coop-marked': 'Coop Marked','obs': 'Coop Obs'}

    folder_path = "temp_output/bilder/"
    utilgjengelige_butikker = set()
    for entry in os.listdir(folder_path):
        butikknavn = finenavn_dict[entry.split('_')[0]]
        utilgjengelige_butikker.add(butikknavn)

    if not utilgjengelige_butikker:
        util_butikkstr = 'Ingen' 
    else:
        util_butikkstr = ''

        for butikk in utilgjengelige_butikker:
            util_butikkstr += butikk + ' '
        util_butikkstr = util_butikkstr[:-1]

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