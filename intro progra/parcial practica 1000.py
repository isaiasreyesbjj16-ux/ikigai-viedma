"""

Examen de práctica — Introducción a la Programación
Ejercicio 1) Salida de programa
python
total = 0
for n in range(1, 9):
    if n % 3 == 0:
        total += 5
    else:
        total += n
print(total)

A. 34 B. 29 C. 31 D. 26

Ejercicio 2) Resolvé el siguiente problema

Consigna: Una librería necesita gestionar su catálogo de libros. Los libros se clasifican por género (Novela, Fantasia, Terror, Infantil) y tienen un estado (Disponible, Prestado).

Estructura de datos: Crear una tupla para representar cada libro, con: codigo, titulo, genero, precio, estado.

Carga de datos:

("LIB-01", "El Nombre del Viento", "Fantasia", 8500, "Disponible")
("LIB-02", "It", "Terror", 7200, "Prestado")
("LIB-03", "Cien Años de Soledad", "Novela", 6000, "Disponible")
("LIB-04", "Matilda", "Infantil", 3500, "Disponible")
("LIB-05", "El Resplandor", "Terror", 6800, "Prestado")

Menú:

a) Listado Total
b) Filtrar por Género
s) Salir del Programa

Requisito: usar al menos una función.

Tomate el tiempo que necesites, sin apuro. Cuando esté listo, lo revisamos y con eso terminamos por hoy.

"""


"""
1 no entra en el if pero si en elif entonces es 0 + 1 =  1

2 no entra pero se suma 1 + 2 = 3

3 entra asi que 3 + 5 = 8

4 no entra pero se suma 8 + 4 = 12

5 no entra 12 + 5 = 17

6 entra asi que se suma 17 + 5 = 22

7 no entra asi que se suma 22 + 7 = 29

8 no entra asi que 29 8 + 29 = 37

"""

catalogo = (
("LIB-01", "El Nombre del Viento", "Fantasia", 8500, "Disponible"),
("LIB-02", "It", "Terror", 7200, "Prestado"),
("LIB-03", "Cien Años de Soledad", "Novela", 6000, "Disponible"),
("LIB-04", "Matilda", "Infantil", 3500, "Disponible"),
("LIB-05", "El Resplandor", "Terror", 6800, "Prestado"),

)

def libros (catalogo):
    for libro in catalogo:
        print (libro [0], libro [1], libro [2], libro [3], libro [4])



def genero (catalogo, cantidades):
    for generos in catalogo:
          if generos [2].lower() == cantidades.lower():
            print (generos [0], generos [1], generos [2], generos [3], generos [4] )

while True:

    print ("a) Listado Total")
    print ("b) Filtrar por Género")
    print ("s) Salir del Programa")

    opcion = input ("Elija una opcion ")

    if opcion == "a":
        libros(catalogo)

    elif opcion == "b":
        generos_disponibles = input("Que genero desea? ")
        genero (catalogo, generos_disponibles)

    elif opcion == "s":
        break

    

