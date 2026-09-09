import unicodedata

from Libro import Libro


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower()


def crear_catalogo():
    libros = []
    libros.append(Libro("9789500000001", "El Principito", "Antoine de Saint-Exupery", 1943, "Novela", 96))
    libros.append(Libro("9789500000002", "Cien anios de soledad", "Gabriel Garcia Marquez", 1967, "Realismo magico", 471))
    libros.append(Libro("9789500000003", "1984", "George Orwell", 1949, "Ciencia ficcion", 328))
    libros.append(Libro("9789500000004", "Don Quijote de la Mancha", "Miguel de Cervantes", 1605, "Novela", 863))
    libros.append(Libro("9789500000005", "El Quijote explicado", "Ana Martinez", 2010, "Ensayo", 120))
    libros.append(Libro("9789500000006", "Dune", "Frank Herbert", 1965, "Ciencia ficcion", 412))
    libros.append(Libro("9789500000007", "Fundacion", "Isaac Asimov", 1951, "Ciencia ficcion", 320))
    libros.append(Libro("9789500000008", "Orgullo y prejuicio", "Jane Austen", 1813, "Novela", 435))
    libros.append(Libro("9789500000009", "Fahrenheit 451", "Ray Bradbury", 1953, "Ciencia ficcion", 249))
    libros.append(Libro("9789500000010", "La casa de los espiritus", "Isabel Allende", 1982, "Realismo magico", 425))
    return libros


def mostrar_todos(libros):
    print("LIBROS DE LA BIBLIOTECA")
    numero = 1
    for libro in libros:
        print(str(numero) + ". " + libro.get_titulo())
        numero = numero + 1


def buscar_por_isbn(libros, isbn):
    encontrado = None
    for libro in libros:
        if libro.get_isbn() == isbn:
            encontrado = libro
    if encontrado is not None:
        print("Libro encontrado.")
        encontrado.mostrar_informacion()
    else:
        print("No se encontro ningun libro con ese ISBN.")


def buscar_por_titulo(libros, fragmento):
    coincidencias = []
    for libro in libros:
        if fragmento.lower() in libro.get_titulo().lower():
            coincidencias.append(libro)
    if coincidencias:
        print("Coincidencias encontradas:")
        for libro in coincidencias:
            print("- " + libro.get_titulo())
    else:
        print("No existen coincidencias.")


def filtrar_por_genero(libros, genero):
    resultados = []
    for libro in libros:
        if normalizar(libro.get_genero()) == normalizar(genero):
            resultados.append(libro)
    if resultados:
        print("Libros del genero " + genero + ":")
        for libro in resultados:
            print("- " + libro.get_titulo())
    else:
        print("No existen libros de ese genero.")


def mostrar_disponibles(libros):
    disponibles = []
    for libro in libros:
        if libro.esta_disponible():
            disponibles.append(libro)
    if disponibles:
        print("LIBROS DISPONIBLES")
        for libro in disponibles:
            libro.mostrar_informacion()
    else:
        print("No hay libros disponibles en este momento.")


def registrar_prestamo(libros, isbn):
    encontrado = None
    for libro in libros:
        if libro.get_isbn() == isbn:
            encontrado = libro
    if encontrado is not None:
        encontrado.prestar()
    else:
        print("No se encontro ningun libro con ese ISBN.")


def registrar_devolucion(libros, isbn):
    encontrado = None
    for libro in libros:
        if libro.get_isbn() == isbn:
            encontrado = libro
    if encontrado is not None:
        encontrado.devolver()
    else:
        print("No se encontro ningun libro con ese ISBN.")


def mostrar_estadisticas(libros):
    total = 0
    disponibles = 0
    for libro in libros:
        total = total + 1
        if libro.esta_disponible():
            disponibles = disponibles + 1
    prestados = total - disponibles
    if total > 0:
        porcentaje_disponibles = disponibles * 100 // total
        porcentaje_prestados = prestados * 100 // total
    else:
        porcentaje_disponibles = 0
        porcentaje_prestados = 0
    print("ESTADISTICAS DE LA BIBLIOTECA")
    print("-------------------------------")
    print("Cantidad total de libros: " + str(total))
    print("Libros disponibles: " + str(disponibles))
    print("Libros prestados: " + str(prestados))
    print("Porcentaje disponibles: " + str(porcentaje_disponibles) + "%")
    print("Porcentaje prestados: " + str(porcentaje_prestados) + "%")


def libro_mas_solicitado(libros):
    if not libros:
        print("No hay libros en la biblioteca.")
        return
    mas_solicitado = libros[0]
    for libro in libros:
        if libro.cantidad_prestamos() > mas_solicitado.cantidad_prestamos():
            mas_solicitado = libro
    print("LIBRO MAS SOLICITADO")
    print("--------------------------------")
    print("Titulo: " + mas_solicitado.get_titulo())
    print("Autor: " + mas_solicitado.get_autor())
    print("Cantidad de prestamos: " + str(mas_solicitado.cantidad_prestamos()))


def libro_mas_antiguo(libros):
    if not libros:
        print("No hay libros en la biblioteca.")
        return
    mas_antiguo = libros[0]
    for libro in libros:
        if libro.get_anio() < mas_antiguo.get_anio():
            mas_antiguo = libro
    print("LIBRO MAS ANTIGUO")
    print("--------------------------------")
    print("Titulo: " + mas_antiguo.get_titulo())
    print("Anio: " + str(mas_antiguo.get_anio()))


def promedio_paginas(libros):
    total_libros = 0
    total_paginas = 0
    for libro in libros:
        total_libros = total_libros + 1
        total_paginas = total_paginas + libro.get_paginas()
    print("Cantidad de libros: " + str(total_libros))
    print("Total de paginas: " + str(total_paginas))
    if total_libros > 0:
        print("Promedio de paginas: " + str(total_paginas // total_libros))
    else:
        print("Promedio de paginas: 0")


def genero_mas_representado(libros):
    generos = []
    cantidades = []
    for libro in libros:
        genero = libro.get_genero()
        indice = -1
        for i in range(len(generos)):
            if generos[i] == genero:
                indice = i
        if indice == -1:
            generos.append(genero)
            cantidades.append(1)
        else:
            cantidades[indice] = cantidades[indice] + 1
    if not generos:
        print("No hay libros en la biblioteca.")
        return
    mejor_indice = 0
    for i in range(len(cantidades)):
        if cantidades[i] > cantidades[mejor_indice]:
            mejor_indice = i
    print("GENERO MAS REPRESENTADO")
    print("--------------------------------")
    print(generos[mejor_indice] + ": " + str(cantidades[mejor_indice]) + " libros")


def mostrar_menu():
    print("========================================")
    print("             BIBLIOTECA")
    print("========================================")
    print("1. Mostrar todos los libros")
    print("2. Buscar libro por ISBN")
    print("3. Buscar libros por titulo")
    print("4. Filtrar libros por genero")
    print("5. Mostrar libros disponibles")
    print("6. Registrar prestamo")
    print("7. Registrar devolucion")
    print("8. Mostrar estadisticas")
    print("9. Mostrar libro mas solicitado")
    print("10. Mostrar libro mas antiguo")
    print("11. Calcular promedio de paginas")
    print("12. Mostrar genero mas representado")
    print("0. Salir")


def main():
    libros = crear_catalogo()
    while True:
        mostrar_menu()
        opcion = input("Seleccione una opcion: ")
        if opcion == "1":
            mostrar_todos(libros)
        elif opcion == "2":
            isbn = input("Ingrese el ISBN: ")
            buscar_por_isbn(libros, isbn)
        elif opcion == "3":
            fragmento = input("Ingrese una palabra del titulo: ")
            buscar_por_titulo(libros, fragmento)
        elif opcion == "4":
            genero = input("Ingrese genero: ")
            filtrar_por_genero(libros, genero)
        elif opcion == "5":
            mostrar_disponibles(libros)
        elif opcion == "6":
            isbn = input("Ingrese el ISBN del libro a prestar: ")
            registrar_prestamo(libros, isbn)
        elif opcion == "7":
            isbn = input("Ingrese el ISBN del libro a devolver: ")
            registrar_devolucion(libros, isbn)
        elif opcion == "8":
            mostrar_estadisticas(libros)
        elif opcion == "9":
            libro_mas_solicitado(libros)
        elif opcion == "10":
            libro_mas_antiguo(libros)
        elif opcion == "11":
            promedio_paginas(libros)
        elif opcion == "12":
            genero_mas_representado(libros)
        elif opcion == "0":
            print("Saliendo del programa.")
            break
        else:
            print("Opcion invalida. Intente nuevamente.")


if __name__ == "__main__":
    main()