DROP DATABASE LABEIT;
CREATE DATABASE LABEIT;
USE LABEIT;

CREATE TABLE Wifi(
    id INT NOT NULL AUTO_INCREMENT,
    nombre_wifi VARCHAR(20),
    contraseña_wifi VARCHAR(50),
    PRIMARY KEY (id)
);

CREATE TABLE Usuario (
    rut VARCHAR(10),
    credencial INT(3),
    email VARCHAR(100),
    contraseña VARCHAR(200),
    nombres VARCHAR(100),
    apellidos VARCHAR(100),
    celular VARCHAR(9),
    region VARCHAR(50),
    ciudad VARCHAR(50),
    comuna VARCHAR(50),
    direccion VARCHAR(50),
    foto VARCHAR(100),
    activo TINYINT(1),
    fecha_registro TIMESTAMP,
    puntaje INT,
    notificacion_email TINYINT(1),
    notificacion_celular TINYINT(1),
    token VARCHAR(10),
    PRIMARY KEY (rut)
);


CREATE TABLE Sanciones(
    id INT NOT NULL AUTO_INCREMENT,
    rut_alumno VARCHAR(10) NOT NULL,
    cantidad_dias INT(2) NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    activo TINYINT(1) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);


CREATE TABLE Credencial(
    id INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(20),
    PRIMARY KEY (id)
);
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';
SET SQL_MODE='ALLOW_INVALID_DATES';

CREATE TABLE Solicitud(
    id INT NOT NULL AUTO_INCREMENT,
    rut_profesor VARCHAR(10),
    rut_alumno VARCHAR(10),
    motivo VARCHAR(1000),
    fecha_registro TIMESTAMP,
    fecha_vencimiento TIMESTAMP,
    estado INT(2),
    PRIMARY KEY(id)
);

CREATE TABLE Estado_solicitud(
    id INT NOT NULL AUTO_INCREMENT,
    descripcion VARCHAR(20),
    PRIMARY KEY(id)
);

CREATE TABLE Detalle_solicitud(
    id INT NOT NULL AUTO_INCREMENT,
    id_solicitud INT,
    id_equipo INT,
    cantidad INT(2),
    fecha_inicio DATETIME,
    fecha_termino DATETIME,
    fecha_devolucion TIMESTAMP,
    estado INT(2),
    numero_cola_espera INT,
    PRIMARY KEY (id)
);
CREATE TABLE Estado_detalle_solicitud(
    id INT NOT NULL AUTO_INCREMENT,
    descripcion VARCHAR(20),
    PRIMARY KEY(id)
);

CREATE TABLE Equipo(
    id INT NOT NULL AUTO_INCREMENT,
    codigo VARCHAR(20) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    marca VARCHAR(50) NOT NULL,
    descripcion VARCHAR(2000),
    fecha_compra DATETIME,
    dias_max_prestamo INT,
    stock INT,
    adquiridos INT,
    imagen VARCHAR(1000),
    fecha_registro DATETIME,
    PRIMARY KEY (id, codigo)
);


CREATE TABLE Etiqueta_equipo(
    id_etiqueta INT,
    id_equipo INT
);

CREATE TABLE Etiqueta(
    id INT,
    descripcion VARCHAR(20),
    PRIMARY KEY (id)
);


CREATE TABLE Motivo_academico_prestamo(
    id INT,
    id_prestamo INT,
    id_curso INT,
    PRIMARY KEY(id)
);

CREATE TABLE Wishlist(
    id INT AUTO_INCREMENT,
    rut_solicitante VARCHAR(10),
    etiqueta_equipo VARCHAR(100),
    modelo_equipo VARCHAR(50),
    marca_equipo VARCHAR(50),
    motivo_academico TINYINT(1),
    carta_motivo VARCHAR(2000),
    PRIMARY KEY(id)
);

CREATE TABLE Url_wishlist(
    url VARCHAR(1000),
    id_wishlist INT
);

CREATE TABLE Motivo_academico_wishlist(
    id INT AUTO_INCREMENT,
    id_wishlist INT,
    id_curso INT,
    PRIMARY KEY(id)
);
CREATE TABLE Curso(
    id INT AUTO_INCREMENT,
    codigo_udp VARCHAR(20),
    nombre VARCHAR(50),
    descripcion VARCHAR(2000),
    PRIMARY KEY(id)
);

CREATE TABLE Seccion(
    id INT,
    id_curso INT,
    rut_profesor VARCHAR(10),
    PRIMARY KEY(id)
);

CREATE TABLE Seccion_alumno(
    id INT AUTO_INCREMENT,
    id_seccion INT,
    rut_alumno VARCHAR (10),
    PRIMARY KEY(id)
);



