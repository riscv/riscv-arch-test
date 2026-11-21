// SPDX-License-Identifier: Apache-2.0

`ifdef ZILX_SUPPORTED
        wildcard bins lxh = {LXH};
        wildcard bins lxw = {LXW};
    `ifdef UDB_MXLEN_64
        wildcard bins lxd = {LXD};
    `endif
        wildcard bins lxhu = {LXHU};
    `ifdef UDB_MXLEN_64
        wildcard bins lxwu = {LXWU};
    `endif
        wildcard bins lxsb = {LXSB};
        wildcard bins lxsh = {LXSH};
        wildcard bins lxsw = {LXSW};
    `ifdef UDB_MXLEN_64
        wildcard bins lxsd = {LXSD};
    `endif
        wildcard bins lxsbu = {LXSBU};
        wildcard bins lxshu = {LXSHU};
    `ifdef UDB_MXLEN_64
        wildcard bins lxswu = {LXSWU};
    `endif
    `ifdef UDB_MXLEN_64
        wildcard bins lxsuwb = {LXSUWB};
    `endif
    `ifdef UDB_MXLEN_64
        wildcard bins lxsuwh = {LXSUWH};
    `endif
    `ifdef UDB_MXLEN_64
        wildcard bins lxsuww = {LXSUWW};
    `endif
    `ifdef UDB_MXLEN_64
        wildcard bins lxsuwd = {LXSUWD};
    `endif
    `ifdef UDB_MXLEN_64
        wildcard bins lxsuwbu = {LXSUWBU};
    `endif
    `ifdef UDB_MXLEN_64
        wildcard bins lxsuwhu = {LXSUWHU};
    `endif
    `ifdef UDB_MXLEN_64
        wildcard bins lxsuwwu = {LXSUWWU};
    `endif
`endif
