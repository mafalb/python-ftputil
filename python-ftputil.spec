
%define pyver  %(%{__python} -c 'import sys ; print sys.version[:3]')

Name:           python-ftputil
Version:        2.4.2
Release: 	0.2
Summary:        The ftputil Python library is a high-level interface to the ftplib module.
Group:          System Environment/Libraries
License:        Open source (revised BSD license)
URL:            http://ftputil.sschwarzer.net/
Source:         ftputil-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Packager: 	Markus Falb <markus.falb@fasel.at>

BuildRequires:  python-devel >= 2.3
Requires:       python-abi = %(%{__python} -c "import sys ; print sys.version[:3]")

%description
ftputil is a high-level FTP client library for the Python programming
language. ftputil implements a virtual file system for accessing FTP servers,
that is, it can generate file-like objects for remote files. The library
supports many functions similar to those in the os, os.path and
shutil modules. ftputil has convenience functions for conditional uploads
and downloads, and handles FTP clients and servers in different timezones.

%prep
%setup -q -n ftputil-%{version}

# Dont include Documentation, RPM has its own ways to pull it in
%{__patch} -b -p1 << NODOCPATCH
diff -urN ftputil-2.4.2.orig/setup.py ftputil-2.4.2/setup.py
--- ftputil-2.4.2.orig/setup.py 2009-11-06 12:41:15.000000000 +0100
+++ ftputil-2.4.2/setup.py  2010-09-13 20:13:02.000000000 +0200
@@ -67,8 +67,6 @@
   version=_version,
   packages=[_package],
   package_dir={_package: ""},
-  data_files=[("doc", ["ftputil.txt", "ftputil.html",
-                       "README.txt", "README.html"])],
   cmdclass={'install_lib': FtputilInstallLib},

   # metadata
NODOCPATCH
 
%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --root=$RPM_BUILD_ROOT \
  --record=INSTALLED_FILES

# avoid byte-compiling `_test_with_statement.py` for Python < 2.5; see
#  http://mail.python.org/pipermail/distutils-sig/2002-June/002894.html
%{__grep} -v "_test_with_statement.py[o,c]" INSTALLED_FILES >INSTALLED_FILES_FIXED
%{__mv} INSTALLED_FILES_FIXED INSTALLED_FILES

sed 's|^\(.*\.pyo\)$|%ghost \1|' < INSTALLED_FILES > %{name}-%{version}.files
find $RPM_BUILD_ROOT%{_libdir}/python%{pyver}/site-packages/* -type d \
  | sed "s|^$RPM_BUILD_ROOT|%dir |" >> %{name}-%{version}.files
find $RPM_BUILD_ROOT -exec chmod go-w {} \;

%clean
rm -rf $RPM_BUILD_ROOT

%files -f %{name}-%{version}.files
%defattr(-,root,root,-)
%doc README.html README.txt ftputil.html ftputil.txt

%changelog
* Tue Sep 14 2010 Markus Falb <markus.falb@fasel.at> 2.4.2-0.2
- Initial packaging
