from datetime import date


class Libro:

    def __init__(self, isbn, titulo, autor, anio, genero, paginas):
        anio_actual = date.today().year

        if not str(isbn).strip():
            raise ValueError("El ISBN no puede estar vacio.")
        if not str(titulo).strip():
            raise ValueError("El titulo no puede estar vacio.")
        if not str(autor).strip():
            raise ValueError("El autor no puede estar vacio.")
        if not str(genero).strip():
            raise ValueError("El genero no puede estar vacio.")
        if not isinstance(anio, int) or anio <= 0 or anio > anio_actual:
            raise ValueError("El anio debe ser un anio valido, no negativo y posterior al anio actual.")
        if not isinstance(paginas, int) or paginas <= 0:
            raise ValueError("La cantidad de paginas debe ser mayor que cero.")

        self.__isbn = str(isbn).strip()
        self.__titulo = str(titulo).strip()
        self.__autor = str(autor).strip()
        self.__anio = anio
        self.__genero = str(genero).strip()
        self.__paginas = paginas
        self.__disponible = True
        self.__cantidad_prestamos = 0

    def prestar(self):
        if self.__disponible:
            self.__disponible = False
            self.__cantidad_prestamos = self.__cantidad_prestamos + 1
            print("Prestamo registrado correctamente.")
        else:
            print("No es posible realizar la operacion: el libro ya esta prestado.")

    def devolver(self):
        if not self.__disponible:
            self.__disponible = True
            print("Devolucion realizada.")
        else:
            print("No es posible realizar la devolucion: el libro ya se encuentra disponible.")

    def esta_disponible(self):
        return self.__disponible

    def cantidad_prestamos(self):
        return self.__cantidad_prestamos

    def get_isbn(self):
        return self.__isbn

    def get_titulo(self):
        return self.__titulo

    def get_autor(self):
        return self.__autor

    def get_anio(self):
        return self.__anio

    def get_genero(self):
        return self.__genero

    def get_paginas(self):
        return self.__paginas

    def mostrar_informacion(self):
        if self.__disponible:
            estado = "Disponible"
        else:
            estado = "Prestado"
        print("-----------------------------------")
        print("ISBN: " + self.__isbn)
        print("Titulo: " + self.__titulo)
        print("Autor: " + self.__autor)
        print("Anio: " + str(self.__anio))
        print("Genero: " + self.__genero)
        print("Paginas: " + str(self.__paginas))
        print("Estado: " + estado)
        print("Prestamos: " + str(self.__cantidad_prestamos))
        print("-----------------------------------")