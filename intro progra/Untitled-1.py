empleados = (
    ("EMP-01", "Juan Perez", "Ventas", 450000, "Activo"),
    ("EMP-02", "Ana Gomez", "Sistemas", 600000, "Activo"),
    ("EMP-03", "Carlos Ruiz", "Administracion", 380000, "Licencia"),
    ("EMP-04", "Marta Diaz", "RRHH", 420000, "Activo"),
    ("EMP-05", "Pedro Lopez", "Sistemas", 550000, "Licencia"),
)

def datos_empleados(empleados):
    for datos in empleados:
        print(datos[0], datos[1], datos[2], datos[3], datos[4])


def filtrar_area(empleados, area):
    for datos in empleados:
        if datos[2].lower() == area.lower():
            print(datos[0], datos[1], datos[2], datos[3], datos[4])


while True:
    print("a) listado total")
    print("b) filtrar por area")
    print("c) salir")
    opcion = input("elegi una opcion: ")

    if opcion == "a":
        datos_empleados(empleados)
    elif opcion == "b":
        area = input("que area quiere averiguar? ")
        filtrar_area(empleados, area)
    elif opcion == "c":
        print("saliendo")
        break

  