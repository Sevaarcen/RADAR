rule scan_anonymous_ftp {
    meta:
        author = "Cole Daubenspeck"
        updated = "20191027"
        description = "When FTP is on target and on port 22, checks for anonymous login (high/critical finding)"
        module = "scan_anon_ftp"
    strings:
        $port = /\[[0-9]+\].port = 22/
        $service = /\[[0-9]+\].service = .*ftp.*/ nocase
    condition:
        all of them
}