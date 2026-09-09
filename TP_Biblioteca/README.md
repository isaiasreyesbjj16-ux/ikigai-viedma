# TP_Biblioteca - Trabajo Practico 1

**Carrera:** Tecnicatura Universitaria en Desarrollo WEB (CURZA)
**Materia:** Introduccion a la Programacion Orientada a Objetos
**Universidad:** Universidad Nacional del Comahue

## Integrantes

- Apellido, Nombre
- Apellido, Nombre

## Descripcion breve del problema

Una biblioteca necesita un pequeno sistema para administrar la informacion de los
libros que posee. El sistema debe permitir registrar libros, consultar y buscar
informacion, conocer cuales estan disponibles, registrar prestamos y devoluciones,
obtener estadisticas e identificar los libros mas solicitados.

El sistema funciona en memoria, utilizando una lista de objetos tipo `Libro`, y se
ejecuta desde la consola a traves de un menu de opciones.

## Descripcion de la clase desarrollada

La clase `Libro` (archivo `Libro.py`) representa un libro con los siguientes
atributos:

- `isbn`
- `titulo`
- `autor`
- `anio`
- `genero`
- `paginas`
- `disponible` (privado, se inicializa en `True`)
- `cantidad_prestamos` (privado, se inicializa en `0`)

Metodos principales:

- `prestar()`: si el libro esta disponible, cambia su estado a no disponible e
  incrementa la cantidad de prestamos.
- `devolver()`: si el libro esta prestado, lo vuelve a marcar como disponible.
- `esta_disponible()`: consulta el estado del libro.
- `cantidad_prestamos()`: consulta cuantas veces fue prestado.
- `mostrar_informacion()`: muestra la informacion relevante del libro.
- Metodos getters para consultar los datos identificatorios del libro.

## Abstraccion

No se representa absolutamente toda la informacion que posee un libro real
(color de tapa, editorial, precio, idioma, etc.), sino solamente los datos que el
sistema necesita para cumplir su funcion: identificar al libro, describirlo y
gestionar prestamos. Esto simplifica el modelo y lo enfoca en el problema.

Se consideraron relevantes: ISBN, titulo, autor, anio de publicacion, genero,
cantidad de paginas, disponibilidad y cantidad de prestamos. La disponibilidad y
la cantidad de prestamos son necesarias para resolver los requerimientos de
prestamos, devoluciones y estadisticas.

## Encapsulamiento

Los atributos `disponible` y `cantidad_prestamos` estan encapsulados (prefijo `__`),
es decir, no se pueden modificar directamente desde fuera de la clase. El estado
solo cambia a traves de los metodos `prestar()` y `devolver()`, que controlan las
reglas de negocio (no se puede prestar un libro ya prestado, no se puede devolver
un libro disponible). Los datos identificatorios se consultan mediante getters.

## Validaciones

Las validaciones se realizan dentro del constructor de la clase `Libro`. Este es
el lugar adecuado porque la clase debe impedir que exista un objeto con datos
invalidos: si los datos no son validos, el objeto no se crea. Asi queda garantizado
que toda instancia de `Libro` siempre este en un estado valido.

Se controla que:

- ISBN, titulo, autor y genero no esten vacios.
- El anio sea un numero mayor que cero y no posterior al anio actual.
- La cantidad de paginas sea mayor que cero.

## Principales algoritmos implementados

- **Mostrar todos los libros:** recorre la lista e imprime los titulos numerados.
- **Buscar por ISBN:** recorre la lista comparando el ISBN ingresado con el de
  cada libro hasta encontrarlo.
- **Buscar por titulo:** recorre la lista y agrega los libros cuyo titulo contiene
  el fragmento ingresado, sin distinguir mayusculas y minusculas.
- **Filtrar por genero:** compara el genero ingresado con el de cada libro,
  ignorando mayusculas, minusculas y acentos.
- **Mostrar disponibles:** filtra por `esta_disponible()` (nunca se accede
  directamente al atributo encapsulado).
- **Registrar prestamo / devolucion:** busca el libro por ISBN y luego llama al
  metodo correspondiente, sin modificar el estado desde fuera de la clase.
- **Estadisticas:** un solo recorrido cuenta total, disponibles, prestados y
  calcula los porcentajes.
- **Libro mas solicitado:** recorre la lista guardando el libro con mayor cantidad
  de prestamos (sin ordenar la lista).
- **Libro mas antiguo:** recorre la lista guardando el libro con menor anio.
- **Promedio de paginas:** acumula paginas y libros en un recorrido y divide.
- **Genero mas representado (desafio):** cuenta las apariciones de cada genero con
  dos listas paralelas y devuelve el de mayor cantidad.

## Respuestas a las preguntas conceptuales

### 1. Abstraccion
No es necesario representar toda la informacion de un libro real porque el sistema
debe resolver un problema puntual. Representar de mas complica el modelo sin
aportar valor. La abstraccion consiste en quedarse con lo esencial: solo los datos
y comportamientos que el problema necesita.

### 2. Modelo
Fueron consideradas relevantes las caracteristicas que permiten identificar y
describir un libro (ISBN, titulo, autor, anio, genero, paginas) y las que permiten
gestionar prestamos y estadisticas (disponibilidad y cantidad de prestamos).

### 3. Encapsulamiento
Que un atributo este encapsulado significa que no puede leerse ni modificarse
directamente desde fuera de la clase. Su acceso esta controlado por metodos, lo
que protege el estado interno del objeto.

### 4. Estado interno
No se debe permitir modificar directamente la disponibilidad desde `main.py`
porque se perderia el control sobre las reglas de negocio: se podria marcar un
libro prestado como disponible sin registrarlo, o prestar un libro sin incrementar
su contador. La clase debe ser la unica responsable de cambiar su estado.

### 5. Metodos
La ventaja de `libro.prestar()` frente a modificar el estado directamente es que el
metodo agrupa toda la logica en un solo lugar, garantizando que siempre se cumplan
las reglas (validar disponibilidad, cambiar el estado e incrementar el contador).
Ademas, si la regla cambia, solo se modifica el metodo.

### 6. Algoritmos
Para encontrar el libro mas solicitado se recorre la lista guardando en una
variable el libro con mayor cantidad de prestamos encontrado hasta el momento. En
cada paso se compara; si el libro actual supera al guardado, se actualiza. Al
terminar el recorrido, la variable contiene el maximo. Es el algoritmo clasico de
"maximo de una coleccion" y no ordena la lista.

### 7. Colecciones
Con `libro1 = Libro(...)` se tiene un objeto suelto: solo se maneja ese libro, con
un nombre fijo. Con `libros = []` (y varios objetos adentro) se puede recorrer,
filtrar, contar y procesar la coleccion completa con bucles, lo que permite
resolver el problema de la biblioteca con cualquier cantidad de libros.

### Diseno
No, no se agregarian los datos de los usuarios a la clase `Libro`. La clase `Libro`
debe tener una sola responsabilidad: representar y administrar libros. Los datos de
los usuarios pertenecen a otra clase (por ejemplo, `Usuario`), que en una unidad
posterior se podra relacionar con `Libro` mediante prestamos.

## Ejecucion

Desde la carpeta del proyecto:

```
python main.py
```

El menu se repite hasta que el usuario elija la opcion 0 (Salir).