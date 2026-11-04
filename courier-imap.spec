Name:		courier-imap
Version:	6.0.7
Release:	2
Summary:	IMAP server that uses Maildirs
License:	GPL
Group:		System/Servers
URL:		https://www.courier-mta.org
Source0:	http://prdownloads.sourceforge.net/courier/%{name}-%{version}.tar.bz2
Source1:	%{name}.imapd-init
Source2:	%{name}.imapd-ssl-init
Source3:	%{name}.pop3d-init
Source4:	%{name}.pop3d-ssl-init
Source5:	%{name}.sysconftool.m4
Patch0:		courier-imap-pam-service-name.patch
Patch1:		courier-imap-6.0.7-openssl-asn1-time.patch
Requires:	courier-base = %{version}
Requires:	courier-authdaemon
Requires(pre):	rpm-helper >= 0.21
Requires(post):	rpm-helper >= 0.19
Requires(preun):	rpm-helper >= 0.19
Requires(postun):	rpm-helper >= 0.19
BuildRequires:	autoconf
BuildRequires:	autoconf-archive
BuildRequires:	automake
BuildRequires:	libtool-base
BuildRequires:	slibtool
BuildRequires:	make
BuildRequires:	procps-ng
BuildRequires:	gdbm-devel
BuildRequires:	pkgconfig(openssl)
BuildRequires:	pkgconfig(libidn2)
BuildRequires:	pkgconfig(libpcre2-8)
BuildRequires:	%mklibname courier-unicode -d
BuildRequires:	locales-en
# 6.0.7 requires courier-authlib >= 0.71
BuildRequires:	courier-authlib-devel >= 0.73.2
BuildRequires:	courier-authdaemon
BuildRequires:	rpm-helper >= 0.21

%description
Courier-IMAP is an IMAP server for Maildir mailboxes. This package contains
the standalone version of the IMAP server that's included in the Courier
mail server package. This package is a standalone version for use with
other mail servers. Do not install this package if you intend to install
the full Courier mail server.  Install the Courier package instead.

%package -n courier-base
Summary:	Courier base files for POP and IMAP servers
Group:		System/Servers
Requires:	procps-ng
Obsoletes:	maildirmake++

%description -n courier-base
This package contains the base files for POP and IMAP servers.

%package -n courier-pop
Summary:	Courier POP servers
Group:		System/Servers
Requires:	courier-base = %{version}
Requires:	courier-authdaemon
Requires(pre):	rpm-helper

%description -n courier-pop
This package contains the POP servers of the Courier-IMAP
server suite.

%prep
%setup -q
%patch 0 -p1
%patch 1 -p1
chmod 644 libs/maildir/README.sharedfolders.html libs/imap/README.proxy.html

# The configure step reruns aclocal and ignores *.m4 files in the top directory.
mkdir -p m4
cp %{SOURCE5} m4/sysconftool.m4

# slibtoolize installs a stub ltmain.sh. aclocal has to see slibtool's
# macros, or the generated libtool script exits before it links.
find . -name configure.ac | while read f; do
	d=$(dirname "$f")
	if grep -qE 'LT_INIT|LIBTOOL' "$f"; then
		mkdir -p "$d/m4"
		cp -a /usr/share/slibtool/slibtool.m4 "$d/m4/"
		cp -a /usr/share/slibtool/sltdl.m4 "$d/m4/"
	fi
done

%build
export slibtool_prefer_sltdl=no
export LD_LIBRARY_PATH="%{_libdir}/courier-authlib"
%serverbuild
# Native configure passes --build and not --host. slibtool then skips
# the ar probe in subdirs that do not canonicalize the host, and the
# static archive recipe tries to execute cr.
%configure2_5x \
    --host=%{_target_platform} \
    --with-notice=unicode \
    --with-db=gdbm \
    --libexec=%{_libdir}/%{name} \
    --datadir=%{_datadir}/%{name} \
    --sysconfdir=%{_sysconfdir}/courier
# Subdirectory rebuilds update m4 files that the top configure depends on.
# Make would then rerun aclocal without the m4 include path.
find . \( -name configure -o -name aclocal.m4 -o -name Makefile.in -o -name '*.h.in' \) -exec touch {} +
find . \( -name config.status -o -name stamp-h -o -name stamp-h1 \) -exec touch {} +

%make

#% check
# force utf8, otherwise tests fails
#export LC_ALL=en_US.UTF-8
#% {__make} check

%install
rm -rf %{buildroot}
install -d -m 755 %{buildroot}%{_initrddir}
install -d -m 755 %{buildroot}%{_sysconfdir}/pam.d
%makeinstall_std

# The top-level names are libtool wrappers copied out of their .libs
# directory. slibtool then installs the wrapper, which execs the build
# tree binary, and find-debuginfo sees no ELF files.
for pair in \
	"libs/imap/.libs/imapd|%{_bindir}/imapd" \
	"libs/imap/.libs/pop3d|%{_bindir}/pop3d" \
	"libs/maildir/.libs/maildirmake|%{_bindir}/maildirmake" \
	"libs/maildir/.libs/maildiracl|%{_bindir}/maildiracl" \
	"libs/maildir/.libs/deliverquota|%{_bindir}/deliverquota" \
	"libs/maildir/.libs/maildirkw|%{_bindir}/maildirkw" \
	"libs/imap/.libs/imaplogin|%{_sbindir}/imaplogin" \
	"libs/imap/.libs/pop3login|%{_sbindir}/pop3login" \
	"libs/makedat/.libs/makedatprog|%{_libdir}/%{name}/makedatprog" \
	"libs/tcpd/.libs/couriertcpd|%{_libdir}/%{name}/couriertcpd" \
	"libs/tcpd/.libs/couriertls|%{_bindir}/couriertls"
do
	src=${pair%|*}
	rel=${pair##*|}
	install -p "$src" "%{buildroot}$rel"
done

# delete upstream init scripts and install custom one
rm -f  %{buildroot}%{_libdir}/%{name}/*.rc
install -m 755 %{SOURCE1} %{buildroot}%{_initrddir}/courier-imapd
install -m 755 %{SOURCE2} %{buildroot}%{_initrddir}/courier-imapd-ssl
install -m 755 %{SOURCE3} %{buildroot}%{_initrddir}/courier-pop3d
install -m 755 %{SOURCE4} %{buildroot}%{_initrddir}/courier-pop3d-ssl
perl -pi -e 's|\@libdir\@|%{_libdir}|' %{buildroot}%{_initrddir}/*

# fix configuration
for file in %{buildroot}%{_sysconfdir}/courier/*.dist; do
    mv $file  %{buildroot}%{_sysconfdir}/courier/`basename $file .dist`
done
chmod 644 %{buildroot}%{_sysconfdir}/courier/imapd*
chmod 644 %{buildroot}%{_sysconfdir}/courier/pop3d*

# fix pam configuration
rm -f %{buildroot}%{_sysconfdir}/pam.d/*
cat > %{buildroot}%{_sysconfdir}/pam.d/courier-imap <<EOF
auth	required	pam_nologin.so
auth	include	system-auth
account	include	system-auth
session	include	system-auth
EOF
cat > %{buildroot}%{_sysconfdir}/pam.d/courier-pop3 <<EOF
auth	required	pam_nologin.so
auth	include	system-auth
account	include	system-auth
session	include	system-auth
EOF

# Maildir
install -d -m 755 %{buildroot}%{_sysconfdir}/skel
(cd %{buildroot}%{_sysconfdir}/skel && %{buildroot}%{_bindir}/maildirmake Maildir)


cat > README.mdv << EOF
Mandriva RPM specific notes

Upgrade
-------
Upstream upgrade procedure consists of shipping new configuration files with
.dist suffix, then running sysconftool script to merge with current
configuration. This packages ships new configuration files with their final
name instead, wich will be saved by rpm as .rpmnew if original ones have been
modified, and run sysconftools script during upgrade automatically.

Init scripts
------------
Upstream init system consist of one unique init script, using values in
configuration files to select wich services to run. This package ships a
replacement init system, composed of four distincts standard services script
for each server, so as to use normal procedure (chkconfig command) to determine
which one to run. As a side-effect, the various *START variables in
configuration files have no effect.
EOF

# replace SSL certs configuration with our own
rm -f %{buildroot}%{_sysconfdir}/courier/imapd.cnf
rm -f %{buildroot}%{_sysconfdir}/courier/pop3d.cnf
perl -pi \
    -e 's|TLS_CERTFILE=.*|TLS_CERTFILE=%{_sysconfdir}/pki/tls/private/courier-imap.pem|'\
    %{buildroot}%{_sysconfdir}/courier/imapd-ssl
perl -pi \
    -e 's|TLS_CERTFILE=.*|TLS_CERTFILE=%{_sysconfdir}/pki/tls/private/courier-pop.pem|'\
    %{buildroot}%{_sysconfdir}/courier/pop3d-ssl

%post
if [ -f %{_sysconfdir}/courier/imapd.rpmnew ]; then
    %{_libdir}/courier-authlib/sysconftool %{_sysconfdir}/courier/imapd.rpmnew >/dev/null
fi
if [ -f %{_sysconfdir}/courier/imapd-ssl.rpmnew ]; then
    %{_libdir}/courier-authlib/sysconftool %{_sysconfdir}/courier/imapd-ssl.rpmnew >/dev/null
fi
%_post_service courier-imapd
%_post_service courier-imapd-ssl
%_create_ssl_certificate courier-imap -b

%preun 
%_preun_service courier-imapd
%_preun_service courier-imapd-ssl

%post -n courier-pop
%_create_ssl_certificate courier-pop -b
if [ -f %{_sysconfdir}/courier/pop3d.rpmnew ]; then
    %{_libdir}/courier-authlib/sysconftool %{_sysconfdir}/courier/pop3d.rpmnew >/dev/null
fi
if [ -f %{_sysconfdir}/courier/pop3d-ssl.rpmnew ]; then
    %{_libdir}/courier-authlib/sysconftool %{_sysconfdir}/courier/pop3d-ssl.rpmnew >/dev/null
fi
%_post_service courier-pop3d
%_post_service courier-pop3d-ssl

%preun -n courier-pop
%_preun_service courier-pop3d
%_preun_service courier-pop3d-ssl

%clean
rm -rf %{buildroot}

%files -n courier-base
%defattr(-,root,root)
%doc INSTALL NEWS README README.mdv
%doc libs/liblock/*.html
%doc libs/maildir/README.*
%doc libs/maildir/maildir.html libs/maildir/maildirkw.html libs/maildir/maildirquota.html libs/maildir/maildirwatch.html
%doc libs/rfc2045/*.html
%doc libs/rfc822/ChangeLog libs/rfc822/rfc822.html
%doc libs/tcpd/README.* libs/tcpd/*.html
%config(noreplace) %{_sysconfdir}/courier/quotawarnmsg.example
%config(noreplace) %{_sysconfdir}/courier/shared
%config(noreplace) %{_sysconfdir}/courier/shared.tmp
%dir %{_sysconfdir}/courier/imapaccess
%config(noreplace) %{_sysconfdir}/skel/Maildir
%{_bindir}/maildirmake
%{_bindir}/deliverquota
%{_bindir}/couriertls
%{_bindir}/maildirkw
%{_bindir}/maildiracl
%{_bindir}/makeimapaccess
%{_bindir}/makedat
%{_sbindir}/sharedindexinstall
%{_sbindir}/sharedindexsplit
%{_mandir}/man1/maildirmake.1*
%{_mandir}/man1/couriertcpd.1*
%{_mandir}/man1/maildiracl.1*
%{_mandir}/man1/maildirkw.1*
%{_mandir}/man8/deliverquota.8*
%{_mandir}/man8/makeimapaccess.8*
%{_libdir}/%{name}

%files
%defattr(-,root,root)
%doc libs/imap/BUGS libs/imap/ChangeLog libs/imap/README.proxy libs/imap/README.proxy.html libs/imap/BUGS.html
%config(noreplace) %{_sysconfdir}/pam.d/courier-imap
%config(noreplace) %{_sysconfdir}/courier/imapd
%config(noreplace) %{_sysconfdir}/courier/imapd-ssl
%{_initrddir}/courier-imapd
%{_initrddir}/courier-imapd-ssl
%{_bindir}/imapd
%{_sbindir}/imaplogin
%{_sbindir}/mkimapdcert
%{_sbindir}/mkdhparams
%{_mandir}/man8/imapd.8*
%{_mandir}/man8/mkimapdcert.8*
%{_mandir}/man8/mkdhparams.8*
%{_datadir}/%{name}/mkimapdcert
%{_datadir}/%{name}/mkdhparams

%files -n courier-pop
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/pam.d/courier-pop3
%config(noreplace) %{_sysconfdir}/courier/pop3d
%config(noreplace) %{_sysconfdir}/courier/pop3d-ssl
%{_initrddir}/courier-pop3d
%{_initrddir}/courier-pop3d-ssl
%{_bindir}/pop3d
%{_sbindir}/pop3login
%{_sbindir}/mkpop3dcert
%{_mandir}/man8/mkpop3dcert.8*
%{_datadir}/%{name}/mkpop3dcert
