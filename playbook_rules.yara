rule scan_anonymous_ftp {
    meta:
        author = "Cole Daubenspeck"
        updated = "20191027"
        description = "When FTP is on target and on port 22, checks for anonymous login (high/critical finding)"
        module = "scan_anon_ftp"
    strings:
        $port = /\[[0-9]+\].port = 21/
        $service = /\[[0-9]+\].service = .*ftp.*/ nocase
    condition:
        all of them
}

rule grab_ftp_file_list {
    meta:
        author = "Cole Daubenspeck"
        updated = "20191031"
        description = "Get a list of files on the anonymous FTP server"
        module = "grab_ftp_file_list"
    strings:
        $vuln = "Anonymous FTP Login"
    condition:
        all of them
}

rule enum_msrpc_all {
    meta:
        author = "Cole Daubenspeck"
        updated = "20200504"
        description = "When MSRPC is running on a Windows machine - a default service"
        module = "enum_msrpc"
    strings:
        $port = /[[0-9]+\].port = 135/
        $service = /\[[0-9]+\].service = .*msrpc.*/ nocase
    condition:
        all of them
}