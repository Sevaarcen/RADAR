rule nmap {
    meta:
        author = "Cole Daubenspeck"
        updated = "20191019"
        description = "This handles execution of nmap parsing"
        module = "parser_nmap"
    strings:
        $scan_report = "Nmap scan report for"
    condition:
        all of them
}